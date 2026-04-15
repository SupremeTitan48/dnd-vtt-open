from __future__ import annotations

from dataclasses import dataclass

Role = str
Resource = str
Action = str


@dataclass(frozen=True)
class PermissionRule:
    allowed_roles: frozenset[Role]
    ownership_required: bool = False


_RULES: dict[tuple[Resource, Action], PermissionRule] = {
    ('session', 'read'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM', 'Player', 'Observer'})),
    ('state', 'read'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM', 'Player', 'Observer'})),
    ('character', 'read'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM', 'Player', 'Observer'}), ownership_required=True),
    ('actor', 'read'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM', 'Player', 'Observer'}), ownership_required=True),
    ('notes', 'read'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('notes', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('encounter_template', 'read'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('encounter_template', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('role_assignment', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('actor_ownership', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('actor', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM', 'Player'}), ownership_required=True),
    ('token', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM', 'Player'}), ownership_required=True),
    ('combat', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('map', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
    ('character_import', 'mutate'): PermissionRule(allowed_roles=frozenset({'GM', 'AssistantGM'})),
}


def resolve_permission_rule(resource: Resource, action: Action) -> PermissionRule:
    key = (resource, action)
    if key not in _RULES:
        raise ValueError(f'Permission rule not found for resource "{resource}" and action "{action}"')
    return _RULES[key]


def is_allowed(
    *,
    role: Role,
    resource: Resource,
    action: Action,
    is_owner: bool = False,
) -> bool:
    rule = resolve_permission_rule(resource, action)
    if role not in rule.allowed_roles:
        return False
    if rule.ownership_required and role not in {'GM', 'AssistantGM'}:
        return is_owner
    return True
