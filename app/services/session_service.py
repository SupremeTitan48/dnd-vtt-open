from __future__ import annotations

import copy
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.policies.access_control import PermissionDeniedError, can_access_resource, can_view_gm_secrets, resolve_actor_role
from content.character_import import import_character_by_format
from content.tutorial_loader import load_tutorial
from engine.game_state import GameStateEngine
from engine.map_state import MapState
from engine.session_store import SessionStore


class SessionConflictError(Exception):
    def __init__(self, current_revision: int):
        super().__init__('Session revision conflict')
        self.current_revision = current_revision


class SessionPermissionError(PermissionDeniedError):
    pass


@dataclass
class CommandContext:
    actor_peer_id: str | None = None
    actor_role: str | None = None
    expected_revision: int | None = None
    idempotency_key: str | None = None


@dataclass
class SessionService:
    store: SessionStore = field(default_factory=lambda: SessionStore(Path('.sessions')))
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    engines: dict[str, GameStateEngine] = field(default_factory=dict)
    allowed_roles: set[str] = field(default_factory=lambda: {'GM', 'AssistantGM', 'Player', 'Observer'})

    def _ensure_metadata(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is not None:
            session.setdefault('characters', [])
            session.setdefault('notes', '')
            session.setdefault('encounter_templates', [])
            session.setdefault('revision', 0)
            session.setdefault('peer_roles', {session.get('host_peer_id', 'host'): 'GM'})
            session.setdefault('idempotency_results', {})
            session.setdefault('actor_owners', {})
            session.setdefault('peer_tokens', {session.get('host_peer_id', 'host'): secrets.token_urlsafe(24)})

    def _normalize_command(self, command: CommandContext | None) -> CommandContext:
        return command or CommandContext()

    def _resolve_role(self, session: dict[str, Any], command: CommandContext) -> str:
        return resolve_actor_role(session, actor_peer_id=command.actor_peer_id, actor_role=command.actor_role)

    def _is_known_peer(self, session: dict[str, Any], command: CommandContext | None) -> bool:
        normalized = self._normalize_command(command)
        if normalized.actor_peer_id is None:
            return True
        return normalized.actor_peer_id == session.get('host_peer_id') or normalized.actor_peer_id in session.get('peers', [])

    def validate_peer_token(self, session_id: str, peer_id: str, peer_token: str | None) -> bool:
        session = self.sessions.get(session_id)
        if not session or not peer_token:
            return False
        self._ensure_metadata(session_id)
        return session.get('peer_tokens', {}).get(peer_id) == peer_token

    def _current_revision(self, session_id: str) -> int:
        self._ensure_metadata(session_id)
        return int(self.sessions[session_id].get('revision', 0))

    def _increment_revision(self, session_id: str) -> int:
        self._ensure_metadata(session_id)
        self.sessions[session_id]['revision'] = self._current_revision(session_id) + 1
        return self.sessions[session_id]['revision']

    def _state_with_revision(self, session_id: str) -> dict[str, Any]:
        engine = self.get_engine(session_id)
        if not engine:
            raise ValueError('Session engine not found')
        snapshot = engine.snapshot()
        snapshot['revision'] = self._current_revision(session_id)
        snapshot['schema_version'] = 1
        return snapshot

    def _prepare_mutation(
        self,
        session_id: str,
        command: CommandContext | None,
        *,
        resource: str,
        action: str = 'mutate',
        is_owner: bool = False,
    ) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        self._ensure_metadata(session_id)
        normalized = self._normalize_command(command)
        if not self._is_known_peer(session, normalized):
            raise SessionPermissionError('Peer is not part of this session')
        current_revision = self._current_revision(session_id)
        if normalized.expected_revision is not None and normalized.expected_revision != current_revision:
            raise SessionConflictError(current_revision=current_revision)
        actor_role = self._resolve_role(session, normalized)
        if not can_access_resource(actor_role, resource, action, is_owner=is_owner):
            raise SessionPermissionError(f'Permission denied for {resource}:{action}')
        if normalized.idempotency_key:
            return session['idempotency_results'].get(normalized.idempotency_key)
        return None

    def _cache_result(self, session_id: str, command: CommandContext | None, result: dict[str, Any]) -> None:
        normalized = self._normalize_command(command)
        if not normalized.idempotency_key:
            return
        self._ensure_metadata(session_id)
        self.sessions[session_id]['idempotency_results'][normalized.idempotency_key] = result

    def is_idempotency_replay(self, session_id: str, command: CommandContext | None) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        normalized = self._normalize_command(command)
        if not normalized.idempotency_key:
            return False
        self._ensure_metadata(session_id)
        return normalized.idempotency_key in session['idempotency_results']

    def _can_view_gm_secrets(self, session: dict[str, Any], command: CommandContext | None) -> bool:
        normalized = self._normalize_command(command)
        role = self._resolve_role(session, normalized)
        return can_view_gm_secrets(role)

    def _is_actor_owner(self, session: dict[str, Any], actor_id: str, command: CommandContext | None) -> bool:
        normalized = self._normalize_command(command)
        actor_peer_id = normalized.actor_peer_id
        if actor_peer_id is None:
            return False
        return actor_peer_id in session.get('actor_owners', {}).get(actor_id, [])

    def _can_view_actor(self, session: dict[str, Any], actor_id: str, command: CommandContext | None) -> bool:
        normalized = self._normalize_command(command)
        role = self._resolve_role(session, normalized)
        return can_access_resource(role, 'actor', 'read', is_owner=self._is_actor_owner(session, actor_id, command))

    def _event_actor_id(self, event: dict[str, Any]) -> str | None:
        payload = event.get('payload', {})
        if not isinstance(payload, dict):
            return None
        event_type = event.get('event_type')
        if event_type == 'actor_updated':
            actor_id = payload.get('actor_id')
            return actor_id if isinstance(actor_id, str) else None
        if event_type in {'token_moved', 'character_imported', 'actor_owner_assigned'}:
            token_id = payload.get('token_id')
            if isinstance(token_id, str):
                return token_id
            actor_id = payload.get('actor_id')
            return actor_id if isinstance(actor_id, str) else None
        return None

    def filter_event_for_view(self, session_id: str, event: dict[str, Any], command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        self._ensure_metadata(session_id)
        if not self._is_known_peer(session, command):
            return None
        if self._can_view_gm_secrets(session, command):
            return event
        filtered = copy.deepcopy(event)
        event_type = filtered.get('event_type')
        payload = filtered.get('payload')
        if not isinstance(payload, dict):
            payload = {}
            filtered['payload'] = payload

        actor_id = self._event_actor_id(filtered)
        if actor_id and not self._can_view_actor(session, actor_id, command):
            filtered['payload'] = {}
            return filtered

        if event_type in {'session_role_assigned', 'actor_owner_assigned'}:
            filtered['payload'] = {}
        return filtered

    def filter_events_for_view(
        self,
        session_id: str,
        events: list[dict[str, Any]],
        command: CommandContext | None = None,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for event in events:
            event_view = self.filter_event_for_view(session_id, event, command)
            if event_view is not None:
                filtered.append(event_view)
        return filtered

    def _filter_session_for_view(self, session: dict[str, Any], command: CommandContext | None) -> dict[str, Any]:
        filtered = {k: v for k, v in session.items() if k != 'idempotency_results'}
        if self._can_view_gm_secrets(session, command):
            return filtered
        filtered = filtered.copy()
        filtered['notes'] = ''
        filtered['encounter_templates'] = []
        filtered.pop('peer_roles', None)
        filtered.pop('actor_owners', None)
        return filtered

    def _filter_state_for_view(self, session_id: str, state: dict[str, Any], command: CommandContext | None) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        if not session or self._can_view_gm_secrets(session, command):
            return state
        normalized = self._normalize_command(command)
        filtered = copy.deepcopy(state)
        filtered_map = filtered.get('map', {})
        filtered_map['blocked_cells'] = []
        actor_id = normalized.actor_peer_id
        owned_actors = {
            actor
            for actor, owners in session.get('actor_owners', {}).items()
            if actor_id is not None and actor_id in owners
        }
        filtered['actors'] = {
            actor_key: actor_value
            for actor_key, actor_value in filtered.get('actors', {}).items()
            if actor_key in owned_actors
        }
        return filtered

    def create_session(
        self,
        session_name: str,
        host_peer_id: str,
        map_width: int = 30,
        map_height: int = 20,
    ) -> dict[str, Any]:
        session_id = secrets.token_hex(4)
        self.sessions[session_id] = {
            'session_id': session_id,
            'session_name': session_name,
            'host_peer_id': host_peer_id,
            'peers': [host_peer_id],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'characters': [],
            'notes': '',
            'encounter_templates': [
                {'template_name': 'Ambush', 'description': 'Fast 3-enemy opener with cover'},
                {'template_name': 'Social Pivot', 'description': 'Negotiation scene that can turn into combat'},
            ],
            'revision': 0,
            'peer_roles': {host_peer_id: 'GM'},
            'idempotency_results': {},
            'actor_owners': {},
            'peer_tokens': {host_peer_id: secrets.token_urlsafe(24)},
        }
        self.engines[session_id] = GameStateEngine(map_state=MapState(width=map_width, height=map_height))
        created = self.sessions[session_id].copy()
        created['host_peer_token'] = self.sessions[session_id]['peer_tokens'][host_peer_id]
        return created

    def get_session(self, session_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if session:
            self._ensure_metadata(session_id)
            if not self._is_known_peer(session, command):
                return None
            return self._filter_session_for_view(session, command)
        return None

    def join_session(self, session_id: str, peer_id: str) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        if peer_id not in session['peers']:
            session['peers'].append(peer_id)
        session.setdefault('peer_roles', {})[peer_id] = session.get('peer_roles', {}).get(peer_id, 'Player')
        self._ensure_metadata(session_id)
        token = session.setdefault('peer_tokens', {}).setdefault(peer_id, secrets.token_urlsafe(24))
        return {'session_id': session_id, 'peers': session['peers'], 'peer_token': token}

    def get_engine(self, session_id: str) -> GameStateEngine | None:
        return self.engines.get(session_id)

    def move_token(self, session_id: str, token_id: str, x: int, y: int, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        session = self.sessions.get(session_id)
        if session is None:
            return None
        cached = self._prepare_mutation(
            session_id,
            command,
            resource='token',
            is_owner=self._is_actor_owner(session, token_id, command),
        )
        if cached is not None:
            return cached
        engine.move_token(token_id, x, y)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def set_initiative(self, session_id: str, order: list[str], command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='combat')
        if cached is not None:
            return cached
        engine.set_initiative(order)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def next_turn(self, session_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='combat')
        if cached is not None:
            return cached
        if engine.combat_tracker.initiative_order:
            engine.advance_turn()
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def update_actor(
        self,
        session_id: str,
        actor_id: str,
        hit_points: int | None,
        add_item: str | None,
        add_condition: str | None,
        command: CommandContext | None = None,
    ) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        session = self.sessions.get(session_id)
        if session is None:
            return None
        cached = self._prepare_mutation(
            session_id,
            command,
            resource='actor',
            is_owner=self._is_actor_owner(session, actor_id, command),
        )
        if cached is not None:
            return cached
        if hit_points is not None:
            engine.set_hit_points(actor_id, hit_points)
        if add_item:
            engine.add_item(actor_id, add_item)
        if add_condition:
            engine.add_condition(actor_id, add_condition)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def set_fog(self, session_id: str, enabled: bool, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='map')
        if cached is not None:
            return cached
        engine.set_fog(enabled)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def reveal_cell(self, session_id: str, x: int, y: int, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='map')
        if cached is not None:
            return cached
        engine.reveal_cell(x, y)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def paint_terrain(self, session_id: str, x: int, y: int, terrain_type: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='map')
        if cached is not None:
            return cached
        engine.paint_terrain(x, y, terrain_type)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def toggle_blocked(self, session_id: str, x: int, y: int, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='map')
        if cached is not None:
            return cached
        engine.toggle_blocked(x, y)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def stamp_asset(self, session_id: str, x: int, y: int, asset_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='character_import')
        if cached is not None:
            return cached
        engine.stamp_asset(x, y, asset_id)
        self._increment_revision(session_id)
        result = self._state_with_revision(session_id)
        self._cache_result(session_id, command, result)
        return result

    def import_character(
        self,
        session_id: str,
        import_format: str,
        payload: str,
        token_id: str | None = None,
        command: CommandContext | None = None,
    ) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        engine = self.get_engine(session_id)
        if not session or not engine:
            return None
        cached = self._prepare_mutation(session_id, command, resource='notes')
        if cached is not None:
            return cached
        self._ensure_metadata(session_id)

        character = import_character_by_format(import_format, payload).model_dump()
        resolved_token = token_id or character['name'].lower().replace(' ', '-')
        session['characters'].append({**character, '_token_id': resolved_token})
        if resolved_token not in engine.map_state.token_positions:
            engine.move_token(resolved_token, 0, 0)
        engine.set_hit_points(resolved_token, character['hit_points'])
        for item in character.get('items', []):
            engine.add_item(resolved_token, item)

        self._increment_revision(session_id)
        result = {
            'character': character,
            'token_id': resolved_token,
            'state': self._state_with_revision(session_id),
        }
        owner_peer_id = self._normalize_command(command).actor_peer_id or session.get('host_peer_id')
        owners = session.setdefault('actor_owners', {}).setdefault(resolved_token, [])
        if owner_peer_id and owner_peer_id not in owners:
            owners.append(owner_peer_id)
        self._cache_result(session_id, command, result)
        return result

    def get_characters(self, session_id: str, command: CommandContext | None = None) -> list[dict[str, Any]] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        self._ensure_metadata(session_id)
        if not self._is_known_peer(session, command):
            return None
        characters = session['characters']
        if self._can_view_gm_secrets(session, command):
            return [{k: v for k, v in character.items() if not k.startswith('_')} for character in characters]
        visible: list[dict[str, Any]] = []
        for character in characters:
            actor_id = character.get('_token_id')
            if isinstance(actor_id, str) and self._can_view_actor(session, actor_id, command):
                visible.append({k: v for k, v in character.items() if not k.startswith('_')})
        return visible

    def set_notes(self, session_id: str, notes: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        cached = self._prepare_mutation(session_id, command, resource='encounter_template')
        if cached is not None:
            return cached
        self._ensure_metadata(session_id)
        session['notes'] = notes
        self._increment_revision(session_id)
        result = {'session_id': session_id, 'notes': notes, 'revision': self._current_revision(session_id)}
        self._cache_result(session_id, command, result)
        return result

    def get_notes(self, session_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        self._ensure_metadata(session_id)
        if not self._is_known_peer(session, command):
            return None
        if not self._can_view_gm_secrets(session, command):
            return {'session_id': session_id, 'notes': ''}
        return {'session_id': session_id, 'notes': session['notes']}

    def add_encounter_template(
        self,
        session_id: str,
        template_name: str,
        description: str,
        command: CommandContext | None = None,
    ) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        cached = self._prepare_mutation(session_id, command, resource='actor_ownership')
        if cached is not None:
            return cached
        self._ensure_metadata(session_id)
        session['encounter_templates'].append({'template_name': template_name, 'description': description})
        self._increment_revision(session_id)
        result = {
            'session_id': session_id,
            'encounter_templates': session['encounter_templates'],
            'revision': self._current_revision(session_id),
        }
        self._cache_result(session_id, command, result)
        return result

    def get_encounter_templates(self, session_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        self._ensure_metadata(session_id)
        if not self._is_known_peer(session, command):
            return None
        if not self._can_view_gm_secrets(session, command):
            return {'session_id': session_id, 'encounter_templates': []}
        return {'session_id': session_id, 'encounter_templates': session['encounter_templates']}

    def get_state(self, session_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        session = self.sessions.get(session_id)
        if session and not self._is_known_peer(session, command):
            return None
        return self._filter_state_for_view(session_id, self._state_with_revision(session_id), command)

    def assign_actor_owner(self, session_id: str, actor_id: str, peer_id: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        cached = self._prepare_mutation(session_id, command, resource='role_assignment')
        if cached is not None:
            return cached
        self._ensure_metadata(session_id)
        if peer_id not in session.get('peers', []):
            raise SessionPermissionError('Peer is not part of this session')
        owners = session.setdefault('actor_owners', {}).setdefault(actor_id, [])
        if peer_id not in owners:
            owners.append(peer_id)
        self._increment_revision(session_id)
        result = {
            'session_id': session_id,
            'actor_id': actor_id,
            'owners': owners,
            'revision': self._current_revision(session_id),
        }
        self._cache_result(session_id, command, result)
        return result

    def assign_session_role(self, session_id: str, peer_id: str, role: str, command: CommandContext | None = None) -> dict[str, Any] | None:
        session = self.sessions.get(session_id)
        if not session:
            return None
        cached = self._prepare_mutation(session_id, command, resource='role_assignment')
        if cached is not None:
            return cached
        self._ensure_metadata(session_id)
        if peer_id not in session.get('peers', []):
            raise SessionPermissionError('Peer is not part of this session')
        if role not in self.allowed_roles:
            raise SessionPermissionError(f'Invalid role: {role}')
        session['peer_roles'][peer_id] = role
        self._increment_revision(session_id)
        result = {
            'session_id': session_id,
            'peer_id': peer_id,
            'role': role,
            'revision': self._current_revision(session_id),
        }
        self._cache_result(session_id, command, result)
        return result

    def save(self, session_id: str) -> Path | None:
        engine = self.get_engine(session_id)
        if not engine:
            return None
        return self.store.save(session_id, engine)

    def load(self, session_id: str) -> dict[str, Any] | None:
        if not (self.store.base_dir / f'{session_id}.json').exists():
            return None
        engine = self.store.load(session_id)
        self.engines[session_id] = engine
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'session_id': session_id,
                'session_name': session_id.replace('-', ' ').title(),
                'host_peer_id': 'loaded-host',
                'peers': ['loaded-host'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'characters': [],
                'notes': '',
                'encounter_templates': [],
                'revision': 0,
                'peer_roles': {'loaded-host': 'GM'},
                'idempotency_results': {},
                'actor_owners': {},
                'peer_tokens': {'loaded-host': secrets.token_urlsafe(24)},
            }
        else:
            self._ensure_metadata(session_id)
        return engine.snapshot()

    def get_tutorial(self, tutorial_path: str = 'packs/starter/tutorials/dm_tutorial_map.json') -> dict[str, Any]:
        tutorial = load_tutorial(tutorial_path)
        return tutorial.model_dump()
