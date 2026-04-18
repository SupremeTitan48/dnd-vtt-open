from __future__ import annotations

from app.session_store_config import create_session_store
from engine.session_store import SessionStore, SqliteSessionStore


def test_create_session_store_defaults_to_json(monkeypatch) -> None:
    monkeypatch.delenv("DND_VTT_SESSION_STORE_BACKEND", raising=False)
    monkeypatch.delenv("DND_VTT_SESSION_STORE_DIR", raising=False)
    store = create_session_store()
    assert isinstance(store, SessionStore)


def test_create_session_store_sqlite_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DND_VTT_SESSION_STORE_BACKEND", "sqlite")
    monkeypatch.setenv("DND_VTT_SESSION_STORE_DIR", str(tmp_path / ".sessions"))
    monkeypatch.setenv("DND_VTT_SESSION_STORE_SQLITE_PATH", str(tmp_path / "sessions.db"))
    store = create_session_store()
    assert isinstance(store, SqliteSessionStore)
