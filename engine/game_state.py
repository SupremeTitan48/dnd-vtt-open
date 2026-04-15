from dataclasses import dataclass, field

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

    def snapshot(self) -> dict:
        return {
            "map": {
                "width": self.map_state.width,
                "height": self.map_state.height,
                "token_positions": self.map_state.token_positions,
            },
            "combat": {
                "initiative_order": self.combat_tracker.initiative_order,
                "turn_index": self.combat_tracker.turn_index,
                "round_number": self.combat_tracker.round_number,
            },
        }
