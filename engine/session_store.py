from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from engine.game_state import GameStateEngine


@dataclass
class SessionStore:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, engine: GameStateEngine) -> Path:
        target = self.base_dir / f"{session_id}.json"
        target.write_text(json.dumps(engine.snapshot(), indent=2))
        return target

    def load(self, session_id: str) -> GameStateEngine:
        source = self.base_dir / f"{session_id}.json"
        payload = json.loads(source.read_text())
        return GameStateEngine.from_snapshot(payload)


@dataclass
class SqliteSessionStore:
    sqlite_path: Path
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    snapshot_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, session_id: str, engine: GameStateEngine) -> Path:
        snapshot_json = json.dumps(engine.snapshot(), separators=(",", ":"))
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions(session_id, snapshot_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    snapshot_json = excluded.snapshot_json,
                    updated_at = excluded.updated_at
                """,
                (session_id, snapshot_json, datetime.now(timezone.utc).isoformat()),
            )
        return self.sqlite_path

    def load(self, session_id: str) -> GameStateEngine:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT snapshot_json FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(session_id)
        payload = json.loads(str(row["snapshot_json"]))
        return GameStateEngine.from_snapshot(payload)
