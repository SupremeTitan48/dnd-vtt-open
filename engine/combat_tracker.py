from dataclasses import dataclass, field


@dataclass
class CombatTracker:
    initiative_order: list[str] = field(default_factory=list)
    turn_index: int = 0
    round_number: int = 1

    def set_order(self, order: list[str]) -> None:
        if not order:
            raise ValueError("Initiative order cannot be empty")
        self.initiative_order = order
        self.turn_index = 0
        self.round_number = 1

    def current_actor(self) -> str:
        if not self.initiative_order:
            raise ValueError("Initiative order is not set")
        return self.initiative_order[self.turn_index]

    def advance_turn(self) -> str:
        if not self.initiative_order:
            raise ValueError("Initiative order is not set")
        self.turn_index = (self.turn_index + 1) % len(self.initiative_order)
        if self.turn_index == 0:
            self.round_number += 1
        return self.current_actor()
