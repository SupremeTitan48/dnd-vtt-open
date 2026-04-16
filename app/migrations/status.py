from __future__ import annotations

from typing import Any

CURRENT_SCHEMA_VERSION = 1
MIN_SUPPORTED_SCHEMA_VERSION = 1


def migration_status(active_sessions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    session_versions: dict[str, int] = {}
    compatible = True
    for session_id, session in active_sessions.items():
        version = int(session.get('schema_version', CURRENT_SCHEMA_VERSION))
        session_versions[session_id] = version
        if version < MIN_SUPPORTED_SCHEMA_VERSION or version > CURRENT_SCHEMA_VERSION:
            compatible = False

    return {
        'current_schema_version': CURRENT_SCHEMA_VERSION,
        'min_supported_schema_version': MIN_SUPPORTED_SCHEMA_VERSION,
        'compatible': compatible,
        'sessions_checked': len(active_sessions),
        'session_versions': session_versions,
    }
