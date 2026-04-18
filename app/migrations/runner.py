from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.migrations.status import CURRENT_SCHEMA_VERSION


@dataclass(frozen=True)
class SessionMigration:
    migration_id: str
    target_version: int
    description: str
    apply: Callable[[dict[str, Any]], None]


def _apply_v2_session_metadata(session: dict[str, Any]) -> None:
    session.setdefault('migration_history', [])
    session.setdefault('schema_version', 1)


def _apply_v3_role_metadata(session: dict[str, Any]) -> None:
    host_peer_id = str(session.get('host_peer_id', 'host'))
    peer_roles = session.setdefault('peer_roles', {})
    if not isinstance(peer_roles, dict):
        peer_roles = {}
        session['peer_roles'] = peer_roles
    peer_roles.setdefault(host_peer_id, 'GM')
    session.setdefault('campaign_id', session.get('session_id', 'campaign'))


SESSION_MIGRATIONS: tuple[SessionMigration, ...] = (
    SessionMigration(
        migration_id='v2_session_metadata',
        target_version=2,
        description='Ensure session migration metadata fields exist',
        apply=_apply_v2_session_metadata,
    ),
    SessionMigration(
        migration_id='v3_role_metadata',
        target_version=3,
        description='Ensure host role and campaign metadata defaults',
        apply=_apply_v3_role_metadata,
    ),
)


def run_session_migrations(session: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    from_version = int(session.get('schema_version', 1))
    pending = [migration for migration in SESSION_MIGRATIONS if migration.target_version > from_version]
    planned = [migration.migration_id for migration in pending]
    if dry_run or not pending:
        return {
            'from_schema_version': from_version,
            'to_schema_version': pending[-1].target_version if pending else from_version,
            'migrated': False,
            'applied_migrations': planned if dry_run else [],
        }

    applied: list[str] = []
    history = session.setdefault('migration_history', [])
    if not isinstance(history, list):
        history = []
        session['migration_history'] = history
    for migration in pending:
        migration.apply(session)
        session['schema_version'] = migration.target_version
        history.append(migration.migration_id)
        applied.append(migration.migration_id)
    session['schema_version'] = max(int(session.get('schema_version', 1)), CURRENT_SCHEMA_VERSION)
    return {
        'from_schema_version': from_version,
        'to_schema_version': int(session.get('schema_version', from_version)),
        'migrated': bool(applied),
        'applied_migrations': applied,
    }
