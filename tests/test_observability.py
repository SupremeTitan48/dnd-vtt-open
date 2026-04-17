from __future__ import annotations

import json
import logging

from app.observability import emit_ops_log


def test_emit_ops_log_writes_structured_json(caplog) -> None:
    logger = logging.getLogger("dnd_vtt.ops.test")
    with caplog.at_level(logging.INFO, logger=logger.name):
        event = emit_ops_log(
            logger,
            event_type="backup_created",
            session_id="s1",
            actor_peer_id="dm",
            detail={"backup_id": "b1"},
        )

    assert event["event_type"] == "backup_created"
    assert event["session_id"] == "s1"
    assert event["actor_peer_id"] == "dm"
    assert event["detail"] == {"backup_id": "b1"}
    assert event["recorded_at"]
    assert caplog.records
    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["event_type"] == "backup_created"
    assert payload["detail"]["backup_id"] == "b1"
