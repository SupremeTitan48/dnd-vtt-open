from dataclasses import dataclass, field

from api_contracts.events import CombatStateUpdated, TokenMoved


@dataclass
class P2PSyncBuffer:
    queued_events: list[dict] = field(default_factory=list)

    def queue_token_move(self, token_id: str, x: int, y: int) -> None:
        event = TokenMoved(token_id=token_id, position={"x": x, "y": y}).model_dump()
        self.queued_events.append({"type": "token_moved", "event": event})

    def queue_combat_update(self, active_actor_id: str, round_number: int) -> None:
        event = CombatStateUpdated(active_actor_id=active_actor_id, round_number=round_number).model_dump()
        self.queued_events.append({"type": "combat_updated", "event": event})

    def flush(self) -> list[dict]:
        events = self.queued_events.copy()
        self.queued_events.clear()
        return events
