from __future__ import annotations

import json
import os
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


class OpsStateStore:
    def record_backup_audit(
        self,
        session_id: str,
        *,
        actor_peer_id: str | None,
        action: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    def get_backup_audit(self, session_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_backup_audit_summary(self) -> tuple[int, dict[str, int]]:
        raise NotImplementedError

    def try_acquire_rate_limit(
        self,
        session_id: str,
        actor_peer_id: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        raise NotImplementedError


@dataclass
class InMemoryOpsStateStore(OpsStateStore):
    backup_audit: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    rate_buckets: dict[tuple[str, str], deque[datetime]] = field(default_factory=dict)

    def record_backup_audit(
        self,
        session_id: str,
        *,
        actor_peer_id: str | None,
        action: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.backup_audit.setdefault(session_id, []).append(
            {
                "session_id": session_id,
                "action": action,
                "actor_peer_id": actor_peer_id,
                "detail": detail or {},
                "recorded_at": _utc_now().isoformat(),
            }
        )

    def get_backup_audit(self, session_id: str) -> list[dict[str, Any]]:
        return list(self.backup_audit.get(session_id, []))

    def get_backup_audit_summary(self) -> tuple[int, dict[str, int]]:
        counts: dict[str, int] = {}
        total = 0
        for entries in self.backup_audit.values():
            for entry in entries:
                action = entry.get("action")
                if isinstance(action, str):
                    counts[action] = counts.get(action, 0) + 1
                    total += 1
        return total, counts

    def try_acquire_rate_limit(
        self,
        session_id: str,
        actor_peer_id: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        key = (session_id, actor_peer_id)
        now = _utc_now()
        bucket = self.rate_buckets.setdefault(key, deque())
        cutoff = now - timedelta(seconds=window_seconds)
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


@dataclass
class SqliteOpsStateStore(OpsStateStore):
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    actor_peer_id TEXT,
                    action TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS backup_rate_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    actor_peer_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def record_backup_audit(
        self,
        session_id: str,
        *,
        actor_peer_id: str | None,
        action: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO backup_audit(session_id, actor_peer_id, action, detail_json, recorded_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (session_id, actor_peer_id, action, json.dumps(detail or {}), _utc_now().isoformat()),
            )

    def get_backup_audit(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, actor_peer_id, action, detail_json, recorded_at
                FROM backup_audit
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [
            {
                "session_id": row["session_id"],
                "actor_peer_id": row["actor_peer_id"],
                "action": row["action"],
                "detail": json.loads(row["detail_json"]),
                "recorded_at": row["recorded_at"],
            }
            for row in rows
        ]

    def get_backup_audit_summary(self) -> tuple[int, dict[str, int]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT action, COUNT(*) AS c
                FROM backup_audit
                GROUP BY action
                """
            ).fetchall()
        counts = {str(row["action"]): int(row["c"]) for row in rows}
        return sum(counts.values()), counts

    def try_acquire_rate_limit(
        self,
        session_id: str,
        actor_peer_id: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> bool:
        now = _utc_now()
        cutoff = (now - timedelta(seconds=window_seconds)).isoformat()
        now_iso = now.isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM backup_rate_events
                WHERE session_id = ? AND actor_peer_id = ? AND recorded_at < ?
                """,
                (session_id, actor_peer_id, cutoff),
            )
            row = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM backup_rate_events
                WHERE session_id = ? AND actor_peer_id = ?
                """,
                (session_id, actor_peer_id),
            ).fetchone()
            count = int(row["c"]) if row else 0
            if count >= limit:
                return False
            conn.execute(
                """
                INSERT INTO backup_rate_events(session_id, actor_peer_id, recorded_at)
                VALUES(?, ?, ?)
                """,
                (session_id, actor_peer_id, now_iso),
            )
            return True


def create_ops_state_store() -> OpsStateStore:
    backend = os.environ.get("DND_VTT_OPS_STATE_BACKEND", "").strip().lower()
    if backend == "sqlite":
        path = Path(os.environ.get("DND_VTT_OPS_STATE_SQLITE_PATH", ".sessions/ops_state.db"))
        return SqliteOpsStateStore(path=path)
    return InMemoryOpsStateStore()
