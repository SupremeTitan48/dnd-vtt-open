from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.combat_tracker import CombatTracker
from engine.inventory_conditions import InventoryConditionsService
from engine.map_state import MapState


@dataclass
class GameStateEngine:
    map_state: MapState
    combat_tracker: CombatTracker = field(default_factory=CombatTracker)
    inventory_conditions: InventoryConditionsService = field(default_factory=InventoryConditionsService)

    def move_token(self, token_id: str, x: int, y: int) -> None:
        self.map_state.move_token(token_id, x, y)

    def set_initiative(self, order: list[str]) -> None:
        self.combat_tracker.set_order(order)

    def advance_turn(self) -> str:
        return self.combat_tracker.advance_turn()

    def set_hit_points(self, actor_id: str, hp: int) -> None:
        self.inventory_conditions.set_hit_points(actor_id, hp)

    def add_item(self, actor_id: str, item_name: str) -> None:
        self.inventory_conditions.add_item(actor_id, item_name)

    def add_condition(self, actor_id: str, condition: str) -> None:
        self.inventory_conditions.add_condition(actor_id, condition)

    def set_fog(self, enabled: bool) -> None:
        self.map_state.toggle_fog(enabled)

    def reveal_cell(self, x: int, y: int) -> None:
        self.map_state.reveal_cell(x, y)

    def hide_cell(self, x: int, y: int) -> None:
        self.map_state.hide_cell(x, y)

    def paint_terrain(self, x: int, y: int, terrain_type: str) -> None:
        self.map_state.paint_terrain(x, y, terrain_type)

    def toggle_blocked(self, x: int, y: int) -> None:
        self.map_state.toggle_blocked(x, y)

    def stamp_asset(self, x: int, y: int, asset_id: str) -> None:
        self.map_state.stamp_asset(x, y, asset_id)

    def compute_visible_cells(self, token_id: str, radius: int) -> set[tuple[int, int]]:
        return self.map_state.recompute_visibility(token_id, radius)

    def set_token_vision_radius(self, token_id: str, radius: int) -> set[tuple[int, int]]:
        return self.map_state.set_token_vision_radius(token_id, radius)

    def snapshot(self) -> dict[str, Any]:
        return {
            "map": {
                "width": self.map_state.width,
                "height": self.map_state.height,
                "token_positions": self.map_state.token_positions,
                "fog_enabled": self.map_state.fog_enabled,
                "revealed_cells": list(self.map_state.revealed_cells),
                "terrain_tiles": {f"{x}:{y}": t for (x, y), t in self.map_state.terrain_tiles.items()},
                "blocked_cells": list(self.map_state.blocked_cells),
                "asset_stamps": {f"{x}:{y}": a for (x, y), a in self.map_state.asset_stamps.items()},
                "visibility_cells_by_token": {
                    token_id: [list(cell) for cell in sorted(cells)]
                    for token_id, cells in self.map_state.visibility_cells_by_token.items()
                },
                "vision_radius_by_token": self.map_state.vision_radius_by_token,
            },
            "combat": {
                "initiative_order": self.combat_tracker.initiative_order,
                "turn_index": self.combat_tracker.turn_index,
                "round_number": self.combat_tracker.round_number,
            },
            "actors": {
                actor_id: {
                    "hit_points": state.hit_points,
                    "held_items": state.held_items,
                    "conditions": state.conditions,
                }
                for actor_id, state in self.inventory_conditions._states.items()
            },
        }

    @classmethod
    def from_snapshot(cls, data: dict[str, Any]) -> "GameStateEngine":
        map_data = data["map"]
        engine = cls(map_state=MapState(width=map_data["width"], height=map_data["height"]))
        engine.map_state.token_positions = {
            token_id: tuple(position)
            for token_id, position in map_data.get("token_positions", {}).items()
        }
        engine.map_state.fog_enabled = map_data.get("fog_enabled", False)
        engine.map_state.revealed_cells = {tuple(cell) for cell in map_data.get("revealed_cells", [])}
        engine.map_state.terrain_tiles = {
            tuple(int(v) for v in key.split(":")): val
            for key, val in map_data.get("terrain_tiles", {}).items()
        }
        engine.map_state.blocked_cells = {tuple(cell) for cell in map_data.get("blocked_cells", [])}
        engine.map_state.asset_stamps = {
            tuple(int(v) for v in key.split(":")): val
            for key, val in map_data.get("asset_stamps", {}).items()
        }
        engine.map_state.visibility_cells_by_token = {
            token_id: {tuple(cell) for cell in cells}
            for token_id, cells in map_data.get("visibility_cells_by_token", {}).items()
        }
        engine.map_state.vision_radius_by_token = {
            token_id: int(radius)
            for token_id, radius in map_data.get("vision_radius_by_token", {}).items()
        }

        combat_data = data.get("combat", {})
        initiative = combat_data.get("initiative_order", [])
        if initiative:
            engine.combat_tracker.set_order(initiative)
            engine.combat_tracker.turn_index = combat_data.get("turn_index", 0)
            engine.combat_tracker.round_number = combat_data.get("round_number", 1)

        for actor_id, actor_data in data.get("actors", {}).items():
            engine.inventory_conditions.ensure_actor(actor_id)
            engine.inventory_conditions.set_hit_points(actor_id, actor_data.get("hit_points", 1))
            for item in actor_data.get("held_items", []):
                engine.inventory_conditions.add_item(actor_id, item)
            for condition in actor_data.get("conditions", []):
                engine.inventory_conditions.add_condition(actor_id, condition)

        return engine
