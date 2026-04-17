from engine.game_state import GameStateEngine
from engine.map_state import MapState
from engine.session_store import SessionStore, SqliteSessionStore


def test_session_save_and_load_roundtrip(tmp_path) -> None:
    store = SessionStore(tmp_path)
    engine = GameStateEngine(map_state=MapState(width=12, height=9))
    engine.move_token("hero", 3, 2)
    engine.set_hit_points("hero", 15)

    store.save("session-a", engine)
    restored = store.load("session-a")

    assert restored.map_state.width == 12
    assert restored.map_state.token_positions["hero"] == (3, 2)
    assert restored.inventory_conditions.get_state("hero").hit_points == 15


def test_sqlite_session_store_roundtrip(tmp_path) -> None:
    store = SqliteSessionStore(sqlite_path=tmp_path / "sessions.db", base_dir=tmp_path / ".sessions")
    engine = GameStateEngine(map_state=MapState(width=8, height=8))
    engine.move_token("hero", 4, 5)

    store.save("session-sqlite", engine)
    restored = store.load("session-sqlite")

    assert restored.map_state.width == 8
    assert restored.map_state.token_positions["hero"] == (4, 5)
