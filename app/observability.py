from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


def emit_ops_log(
    logger: logging.Logger,
    *,
    event_type: str,
    session_id: str,
    actor_peer_id: str | None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "event_type": event_type,
        "session_id": session_id,
        "actor_peer_id": actor_peer_id,
        "detail": detail or {},
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(json.dumps(event, sort_keys=True))
    return event
