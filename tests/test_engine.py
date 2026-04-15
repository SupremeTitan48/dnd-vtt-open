from engine.game_state import GameStateEngine
from engine.map_state import MapState


def test_map_movement_and_snapshot() -> None:
    engine = GameStateEngine(map_state=MapState(width=10, height=10))
    engine.move_token("hero", 3, 4)
    snap = engine.snapshot()
    assert snap["map"]["token_positions"]["hero"] == (3, 4)


def test_combat_round_advances() -> None:
    engine = GameStateEngine(map_state=MapState(width=5, height=5))
    engine.set_initiative(["a", "b"])
    assert engine.combat_tracker.current_actor() == "a"
    engine.advance_turn()
    assert engine.combat_tracker.current_actor() == "b"
    engine.advance_turn()
    assert engine.combat_tracker.round_number == 2


def test_snapshot_roundtrip_restores_actor_state() -> None:
    engine = GameStateEngine(map_state=MapState(width=10, height=10))
    engine.move_token("hero", 5, 5)
    engine.set_initiative(["hero"])
    engine.set_hit_points("hero", 12)
    engine.add_item("hero", "Rope")
    engine.add_condition("hero", "Blessed")

    restored = GameStateEngine.from_snapshot(engine.snapshot())
    restored_state = restored.inventory_conditions.get_state("hero")

    assert restored.map_state.token_positions["hero"] == (5, 5)
    assert restored_state.hit_points == 12
    assert "Rope" in restored_state.held_items
    assert "Blessed" in restored_state.conditions


def test_map_layer_operations_roundtrip() -> None:
    engine = GameStateEngine(map_state=MapState(width=8, height=8))
    engine.paint_terrain(1, 1, "water")
    engine.toggle_blocked(2, 2)
    engine.stamp_asset(3, 3, "tree")

    restored = GameStateEngine.from_snapshot(engine.snapshot())
    assert restored.map_state.terrain_tiles[(1, 1)] == "water"
    assert (2, 2) in restored.map_state.blocked_cells
    assert restored.map_state.asset_stamps[(3, 3)] == "tree"
