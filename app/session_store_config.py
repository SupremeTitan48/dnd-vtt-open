from __future__ import annotations

import os
from pathlib import Path

from engine.session_store import SessionStore, SqliteSessionStore


def create_session_store() -> SessionStore | SqliteSessionStore:
    base_dir = Path(os.environ.get("DND_VTT_SESSION_STORE_DIR", ".sessions"))
    backend = os.environ.get("DND_VTT_SESSION_STORE_BACKEND", "json").strip().lower()
    if backend == "sqlite":
        sqlite_path = Path(os.environ.get("DND_VTT_SESSION_STORE_SQLITE_PATH", str(base_dir / "sessions.db")))
        return SqliteSessionStore(sqlite_path=sqlite_path, base_dir=base_dir)
    return SessionStore(base_dir=base_dir)
