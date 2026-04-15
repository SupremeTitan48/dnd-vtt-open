from engine.game_state import GameStateEngine
from engine.map_state import MapState


def test_map_movement_and_snapshot() -> None:
    engine = GameStateEngine(map_state=MapState(width=10, height=10))
    engine.move_token("hero", 3, 4)
    snap = engine.snapshot()
    assert snap["map"]["token_positions"]["hero"] == (3, 4)


def test_combat_round_advances() -> None:
    engine = GameStateEngine(map_state=MapState(width=5, height=5))
    engine.combat_tracker.set_order(["a", "b"])
    assert engine.combat_tracker.current_actor() == "a"
    engine.combat_tracker.advance_turn()
    assert engine.combat_tracker.current_actor() == "b"
    engine.combat_tracker.advance_turn()
    assert engine.combat_tracker.round_number == 2
