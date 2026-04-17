import time

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


def test_lighting_and_vision_roundtrip_defaults_and_updates() -> None:
    engine = GameStateEngine(map_state=MapState(width=8, height=8))
    engine.move_token("hero", 1, 1)
    engine.set_scene_lighting("night")
    engine.set_token_light(
        "hero",
        bright_radius=3,
        dim_radius=6,
        color="#ffaa66",
        enabled=True,
    )
    engine.set_token_vision_mode("hero", "darkvision")

    restored = GameStateEngine.from_snapshot(engine.snapshot())
    assert restored.map_state.scene_lighting_preset == "night"
    assert restored.map_state.token_light_by_token["hero"]["bright_radius"] == 3
    assert restored.map_state.token_light_by_token["hero"]["dim_radius"] == 6
    assert restored.map_state.token_light_by_token["hero"]["color"] == "#ffaa66"
    assert restored.map_state.token_light_by_token["hero"]["enabled"] is True
    assert restored.map_state.vision_mode_by_token["hero"] == "darkvision"

def test_visibility_respects_blockers() -> None:
    engine = GameStateEngine(map_state=MapState(width=7, height=3))
    engine.move_token("hero", 1, 1)
    engine.toggle_blocked(2, 1)

    visible = engine.compute_visible_cells("hero", 1)
    assert (2, 1) in visible
    assert (3, 1) not in visible


def test_visibility_respects_map_bounds() -> None:
    engine = GameStateEngine(map_state=MapState(width=4, height=4))
    engine.move_token("edge", 0, 0)
    visible = engine.compute_visible_cells("edge", 2)
    for x, y in visible:
        assert 0 <= x < 4
        assert 0 <= y < 4


def test_visibility_cache_reuses_previous_query() -> None:
    state = MapState(width=20, height=20)
    state.move_token("hero", 10, 10)
    first = state.recompute_visibility("hero", 6)
    first_misses = state.visibility_cache_misses
    second = state.recompute_visibility("hero", 6)
    assert second == first
    assert state.visibility_cache_misses == first_misses
    assert state.visibility_cache_hits >= 1


def test_visibility_cache_invalidates_after_blocker_change() -> None:
    state = MapState(width=20, height=20)
    state.move_token("hero", 10, 10)
    before = state.recompute_visibility("hero", 6)
    misses_before = state.visibility_cache_misses
    state.toggle_blocked(11, 10)
    after = state.recompute_visibility("hero", 6)
    assert state.visibility_cache_misses > misses_before
    assert before != after


def test_blocker_revision_advances_when_blocked_cells_change() -> None:
    state = MapState(width=10, height=10)
    assert state.blocker_revision == 0
    state.toggle_blocked(1, 1)
    assert state.blocker_revision == 1
    state.toggle_blocked(1, 1)
    assert state.blocker_revision == 2


def test_cached_visibility_workload_stays_within_budget() -> None:
    state = MapState(width=60, height=60)
    state.move_token("hero", 30, 30)
    for x in range(20, 40):
        if x % 2 == 0:
            state.toggle_blocked(x, 32)

    state.recompute_visibility("hero", 10)
    start = time.perf_counter()
    for _ in range(250):
        state.recompute_visibility("hero", 10)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.75
