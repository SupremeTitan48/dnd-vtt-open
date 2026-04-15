from dataclasses import dataclass, field


@dataclass
class CombatantState:
    held_items: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    hit_points: int = 1


class InventoryConditionsService:
    def __init__(self) -> None:
        self._states: dict[str, CombatantState] = {}

    def ensure_actor(self, actor_id: str) -> None:
        self._states.setdefault(actor_id, CombatantState())

    def set_hit_points(self, actor_id: str, hp: int) -> None:
        self.ensure_actor(actor_id)
        self._states[actor_id].hit_points = max(0, hp)

    def add_item(self, actor_id: str, item_name: str) -> None:
        self.ensure_actor(actor_id)
        self._states[actor_id].held_items.append(item_name)

    def add_condition(self, actor_id: str, condition: str) -> None:
        self.ensure_actor(actor_id)
        if condition not in self._states[actor_id].conditions:
            self._states[actor_id].conditions.append(condition)

    def get_state(self, actor_id: str) -> CombatantState:
        self.ensure_actor(actor_id)
        return self._states[actor_id]
