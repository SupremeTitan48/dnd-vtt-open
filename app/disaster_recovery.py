from __future__ import annotations

from typing import Any

from app.services.session_service import SessionPermissionError, SessionService


def run_backup_restore_drill(
    service: SessionService,
    *,
    session_id: str,
    token_id: str = "hero",
    baseline_position: tuple[int, int] = (2, 2),
    changed_position: tuple[int, int] = (7, 7),
) -> dict[str, Any]:
    """Validate backup/restore roundtrip by mutating and recovering token state."""
    baseline = service.move_token(session_id, token_id, baseline_position[0], baseline_position[1])
    if baseline is None:
        raise SessionPermissionError("Session not found for backup/restore drill")
    backup = service.backup(session_id)
    if backup is None:
        raise SessionPermissionError("Unable to create backup during drill")
    backup_id = str(backup["backup_id"])

    changed = service.move_token(session_id, token_id, changed_position[0], changed_position[1])
    if changed is None:
        raise SessionPermissionError("Unable to mutate session during drill")

    restored = service.restore_backup(session_id, backup_id)
    if restored is None:
        raise SessionPermissionError("Unable to restore backup during drill")

    map_state = restored.get("map", {})
    token_positions = map_state.get("token_positions", {})
    restored_position_raw = token_positions.get(token_id)
    restored_position = list(restored_position_raw) if isinstance(restored_position_raw, (list, tuple)) else restored_position_raw
    ok = restored_position == [baseline_position[0], baseline_position[1]]
    return {
        "session_id": session_id,
        "ok": ok,
        "backup_id": backup_id,
        "token_id": token_id,
        "baseline_position": [baseline_position[0], baseline_position[1]],
        "changed_position": [changed_position[0], changed_position[1]],
        "restored_position": restored_position,
        "restored_revision": restored.get("revision"),
    }
