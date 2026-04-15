from dataclasses import dataclass, field

from api_contracts.events import CombatStateUpdated, TokenMoved


@dataclass
class P2PSyncBuffer:
    queued_events: list[dict] = field(default_factory=list)
    _next_seq: int = 1

    def _enqueue(self, event_type: str, event: dict) -> None:
        self.queued_events.append({"seq": self._next_seq, "type": event_type, "event": event})
        self._next_seq += 1

    def queue_token_move(self, token_id: str, x: int, y: int) -> None:
        event = TokenMoved(token_id=token_id, position={"x": x, "y": y}).model_dump()
        self._enqueue("token_moved", event)

    def queue_combat_update(self, active_actor_id: str, round_number: int) -> None:
        event = CombatStateUpdated(active_actor_id=active_actor_id, round_number=round_number).model_dump()
        self._enqueue("combat_updated", event)

    def acknowledge(self, upto_seq: int) -> None:
        self.queued_events = [entry for entry in self.queued_events if entry["seq"] > upto_seq]

    def flush(self) -> list[dict]:
        return self.queued_events.copy()
