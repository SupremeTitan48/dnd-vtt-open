from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from inspect import isawaitable
from typing import Any, Callable
from uuid import uuid4


@dataclass
class SessionEvent:
    session_id: str
    event_type: str
    payload: dict[str, Any]
    revision: int | None = None
    event_id: str | None = None
    timestamp: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'event_id': self.event_id or str(uuid4()),
            'event_type': self.event_type,
            'session_id': self.session_id,
            'revision': self.revision,
            'timestamp': self.timestamp or datetime.now(timezone.utc).isoformat(),
            'payload': self.payload,
        }


class SessionEventPublisher:
    def __init__(self, sinks: list[Callable[[dict[str, Any]], Any]] | None = None):
        self._sinks = sinks or []

    async def publish(self, event: SessionEvent) -> dict[str, Any]:
        event_payload = event.as_dict()
        for sink in self._sinks:
            result = sink(event_payload)
            if isawaitable(result):
                await result
        return event_payload
