from __future__ import annotations

from typing import Any

from app.policies.permission_matrix import is_allowed


class PermissionDeniedError(Exception):
    pass


def resolve_actor_role(session: dict[str, Any], actor_peer_id: str | None, actor_role: str | None) -> str:
    peer_roles = session.get('peer_roles', {})
    if actor_peer_id and actor_peer_id in peer_roles:
        return peer_roles[actor_peer_id]
    if actor_peer_id == session.get('host_peer_id'):
        return 'GM'
    if actor_peer_id:
        # Unknown peers are treated as least-privilege observers.
        return 'Observer'
    if actor_role:
        return actor_role
    return 'GM'


def require_any_role(actor_role: str, allowed_roles: set[str]) -> None:
    if actor_role in allowed_roles:
        return
    raise PermissionDeniedError(f'Role "{actor_role}" is not allowed for this action')


def can_view_gm_secrets(actor_role: str) -> bool:
    return is_allowed(role=actor_role, resource='notes', action='read')


def can_access_resource(actor_role: str, resource: str, action: str, *, is_owner: bool = False) -> bool:
    return is_allowed(role=actor_role, resource=resource, action=action, is_owner=is_owner)
