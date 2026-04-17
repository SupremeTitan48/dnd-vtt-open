from __future__ import annotations

import json
import logging
import secrets
from asyncio import gather
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from api.schemas import (
    AssetLibraryItemRequest,
    ActorOwnershipRequest,
    ActorStateRequest,
    BackupRequest,
    CharacterImportRequest,
    ChatMessageRequest,
    CommandContextRequest,
    EncounterTemplateRequest,
    FogRequest,
    InitiativeRequest,
    JoinRequest,
    MoveTokenRequest,
    NextTurnRequest,
    PaintTerrainRequest,
    PruneBackupsByAgeRequest,
    PruneBackupsRequest,
    PluginRequest,
    MacroRequest,
    MigrateSessionRequest,
    RollTemplateRequest,
    RelayTicketRequest,
    RecomputeVisibilityRequest,
    TokenVisionRequest,
    TokenLightRequest,
    SceneLightingRequest,
    RevealCellRequest,
    ShareRequest,
    SessionCreateRequest,
    SheetActionRollRequest,
    JournalEntryRequest,
    JournalEntryUpdateRequest,
    HandoutRequest,
    HandoutUpdateRequest,
    HideCellRequest,
    ImportBackupRequest,
    SessionRoleRequest,
    SessionNotesRequest,
    SignalMessage,
    StampAssetRequest,
    ToggleBlockedRequest,
    RunMacroRequest,
    RestoreBackupRequest,
    RenderRollTemplateRequest,
    InstallPackRequest,
    ToggleModuleRequest,
    ExecutePluginHookRequest,
)
from app.commands.dispatcher import CommandDispatcher, InvalidCommandPayloadError, UnknownCommandError
from app.events.file_event_log import JsonlEventLogSink
from app.events.publisher import SessionEvent, SessionEventPublisher
from app.backup_rate_limit_config import get_backup_rate_limit_config
from app.observability import emit_ops_log
from app.ops_state_store import create_ops_state_store
from app.policies.access_control import can_view_gm_secrets, resolve_actor_role
from app.services.session_service import CommandContext, SessionConflictError, SessionPermissionError, SessionService

router = APIRouter(prefix='/api', tags=['tabletop'])
session_service = SessionService()
command_dispatcher = CommandDispatcher(session_service)
_message_bus: dict[str, list[SignalMessage]] = {}
_ws_connections: dict[str, list[tuple[WebSocket, CommandContext]]] = {}
_event_log_sink = JsonlEventLogSink()
_event_publisher = SessionEventPublisher(sinks=[_event_log_sink])
_ops_state_store = create_ops_state_store()
_ops_logger = logging.getLogger('dnd_vtt.ops')


def _to_command_context(command: CommandContextRequest | None) -> CommandContext:
    if command is None:
        return CommandContext()
    return CommandContext(
        actor_peer_id=command.actor_peer_id,
        actor_token=command.actor_token,
        actor_role=command.actor_role,
        expected_revision=command.expected_revision,
        idempotency_key=command.idempotency_key,
    )


async def _publish_session_event(session_id: str, event_type: str, payload: dict, revision: int | None = None) -> None:
    event_payload = await _event_publisher.publish(
        SessionEvent(session_id=session_id, event_type=event_type, payload=payload, revision=revision)
    )
    dead: list[WebSocket] = []
    sockets = _ws_connections.get(session_id, [])
    send_coroutines = []
    send_targets: list[WebSocket] = []
    for ws, context in sockets:
        filtered_event = session_service.filter_event_for_view(session_id, event_payload, context)
        if filtered_event is None:
            dead.append(ws)
            continue
        send_coroutines.append(ws.send_text(json.dumps(filtered_event)))
        send_targets.append(ws)
    results = await gather(*send_coroutines, return_exceptions=True) if send_coroutines else []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            dead.append(send_targets[idx])
    if dead:
        _ws_connections[session_id] = [(ws, ctx) for ws, ctx in sockets if ws not in dead]


def _dispatch_command(session_id: str, action: str, payload: dict, command: CommandContextRequest | None) -> dict[str, Any]:
    try:
        result = command_dispatcher.dispatch(
            session_id=session_id,
            action=action,
            payload=payload,
            command=_to_command_context(command),
        )
    except UnknownCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidCommandPayloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SessionConflictError as exc:
        raise HTTPException(status_code=409, detail={'error': 'revision_conflict', 'current_revision': exc.current_revision}) from exc
    except SessionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return result


def _is_idempotency_replay(session_id: str, command: CommandContextRequest | None) -> bool:
    return session_service.is_idempotency_replay(session_id, _to_command_context(command))


def _validate_read_identity(session_id: str, actor_peer_id: str | None, actor_token: str | None) -> None:
    if actor_peer_id and not session_service.validate_peer_token(session_id, actor_peer_id, actor_token):
        raise HTTPException(status_code=403, detail='invalid actor token')


def _require_read_identity(session_id: str, actor_peer_id: str | None, actor_token: str | None) -> None:
    if not actor_peer_id:
        raise HTTPException(status_code=403, detail='actor_peer_id is required')
    if not session_service.validate_peer_token(session_id, actor_peer_id, actor_token):
        raise HTTPException(status_code=403, detail='invalid actor token')


def _require_command_identity(session_id: str, command: CommandContextRequest | None) -> None:
    if command is None or not command.actor_peer_id:
        raise HTTPException(status_code=403, detail='command.actor_peer_id is required')
    if not session_service.validate_peer_token(session_id, command.actor_peer_id, command.actor_token):
        raise HTTPException(status_code=403, detail='invalid actor token')


def _require_privileged_gm_read(
    session_id: str,
    *,
    actor_peer_id: str,
    actor_token: str | None,
    actor_role: str | None = None,
    operation_name: str = 'operation',
) -> None:
    if not session_service.validate_peer_token(session_id, actor_peer_id, actor_token):
        raise HTTPException(status_code=403, detail='invalid actor token')
    session = session_service.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    resolved_role = resolve_actor_role(session, actor_peer_id=actor_peer_id, actor_role=actor_role)
    if not can_view_gm_secrets(resolved_role):
        raise HTTPException(status_code=403, detail=f'{operation_name} requires GM or AssistantGM role')


def _check_backup_rate_limit(session_id: str, actor_peer_id: str) -> None:
    limit, window_seconds = get_backup_rate_limit_config()
    if not _ops_state_store.try_acquire_rate_limit(
        session_id,
        actor_peer_id,
        limit=limit,
        window_seconds=window_seconds,
    ):
        _ops_state_store.record_backup_audit(
            session_id,
            actor_peer_id=actor_peer_id,
            action='backup_rate_limited',
            detail={'limit': limit, 'window_seconds': window_seconds},
        )
        emit_ops_log(
            _ops_logger,
            event_type='backup_rate_limited',
            session_id=session_id,
            actor_peer_id=actor_peer_id,
            detail={'limit': limit, 'window_seconds': window_seconds},
        )
        raise HTTPException(status_code=429, detail='backup operation rate limit exceeded')


@router.post('/sessions')
def create_session(request: SessionCreateRequest) -> dict:
    return session_service.create_session(
        session_name=request.session_name,
        host_peer_id=request.host_peer_id,
        campaign_id=request.campaign_id,
        map_width=request.map_width,
        map_height=request.map_height,
    )


@router.get('/sessions/{session_id}')
def get_session(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _validate_read_identity(session_id, actor_peer_id, actor_token)
    session = session_service.get_session(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    return session


@router.post('/sessions/{session_id}/join')
def join_session(session_id: str, request: JoinRequest) -> dict:
    result = session_service.join_session(session_id, request.peer_id)
    if not result:
        raise HTTPException(status_code=404, detail='Session not found')
    return result


@router.get('/sessions/{session_id}/state')
def get_state(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _validate_read_identity(session_id, actor_peer_id, actor_token)
    state = session_service.get_state(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if state is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'state': state}


@router.get('/sessions/{session_id}/events/replay')
def replay_events(
    session_id: str,
    after_revision: int = 0,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    if after_revision < 0:
        raise HTTPException(status_code=400, detail='after_revision must be >= 0')
    if not actor_peer_id:
        raise HTTPException(status_code=403, detail='actor_peer_id is required')
    if not session_service.validate_peer_token(session_id, actor_peer_id, actor_token):
        raise HTTPException(status_code=403, detail='invalid actor token')
    session = session_service.get_session(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if not session:
        raise HTTPException(status_code=404, detail='Session not found')
    return {
        'session_id': session_id,
        'events': session_service.filter_events_for_view(
            session_id,
            _event_log_sink.read_after_revision(session_id, after_revision),
            command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
        ),
    }


@router.post('/sessions/{session_id}/move-token')
async def move_token(session_id: str, request: MoveTokenRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(
        session_id,
        'move_token',
        {'token_id': request.token_id, 'x': request.x, 'y': request.y},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id, 'token_moved', {'token_id': request.token_id, 'x': request.x, 'y': request.y}, revision=state.get('revision')
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/initiative')
async def set_initiative(session_id: str, request: InitiativeRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(session_id, 'set_initiative', {'order': request.order}, request.command)
    if not replay:
        await _publish_session_event(session_id, 'initiative_set', {'order': request.order}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/next-turn')
async def next_turn(session_id: str, request: NextTurnRequest | None = None) -> dict:
    command = request.command if request else None
    replay = _is_idempotency_replay(session_id, command)
    state = _dispatch_command(session_id, 'next_turn', {}, command)
    if not replay:
        await _publish_session_event(session_id, 'turn_advanced', state.get('combat', {}), revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/actor-state')
async def update_actor_state(session_id: str, request: ActorStateRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(
        session_id,
        'update_actor',
        {
            'actor_id': request.actor_id,
            'hit_points': request.hit_points,
            'add_item': request.add_item,
            'add_condition': request.add_condition,
            'armor_class': request.armor_class,
            'max_hit_points': request.max_hit_points,
            'current_hit_points': request.current_hit_points,
            'concentration': request.concentration,
            'saves': request.saves,
            'skills': request.skills,
            'spell_slots': request.spell_slots,
            'inventory_add': request.inventory_add,
            'inventory_remove': request.inventory_remove,
        },
        request.command,
    )
    if not replay:
        await _publish_session_event(session_id, 'actor_updated', {'actor_id': request.actor_id}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/sheet-actions/roll')
async def roll_sheet_action(session_id: str, request: SheetActionRollRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    result = _dispatch_command(
        session_id,
        'roll_sheet_action',
        {
            'actor_id': request.actor_id,
            'action_type': request.action_type,
            'action_key': request.action_key,
            'advantage_mode': request.advantage_mode,
            'visibility_mode': request.visibility_mode,
        },
        request.command,
    )
    result = dict(result)
    authoritative_payload = result.get('_authoritative_event_payload', {})
    if not isinstance(authoritative_payload, dict) or not authoritative_payload:
        authoritative_payload = {
            'actor_id': request.actor_id,
            'action_type': request.action_type,
            'action_key': request.action_key,
            'advantage_mode': request.advantage_mode,
            'visibility_mode': request.visibility_mode,
            'formula': result.get('formula'),
            'total': result.get('total'),
        }
    if not replay:
        await _publish_session_event(
            session_id,
            'sheet_action_rolled',
            authoritative_payload,
            revision=result.get('revision'),
        )
    result.pop('_authoritative_event_payload', None)
    return result


@router.post('/sessions/{session_id}/chat/messages')
async def send_chat_message(session_id: str, request: ChatMessageRequest) -> dict:
    replay = session_service.is_chat_idempotency_replay(session_id, _to_command_context(request.command))
    result = _dispatch_command(
        session_id,
        'send_chat_message',
        {
            'content': request.content,
            'kind': request.kind,
            'visibility_mode': request.visibility_mode,
            'whisper_targets': request.whisper_targets,
        },
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'chat_message',
            {
                'message_id': result.get('message_id'),
                'sender_peer_id': result.get('sender_peer_id'),
                'kind': result.get('kind'),
                'content': result.get('content'),
                'visibility_mode': result.get('visibility_mode'),
                'whisper_targets': result.get('whisper_targets', []),
            },
            revision=result.get('revision'),
        )
    return result


@router.post('/sessions/{session_id}/actor-ownership')
async def assign_actor_ownership(session_id: str, request: ActorOwnershipRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    ownership = _dispatch_command(
        session_id,
        'assign_actor_owner',
        {'actor_id': request.actor_id, 'peer_id': request.peer_id},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'actor_owner_assigned',
            {'actor_id': request.actor_id, 'peer_id': request.peer_id},
            revision=ownership.get('revision'),
        )
    return ownership


@router.post('/sessions/{session_id}/roles')
async def assign_session_role(session_id: str, request: SessionRoleRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    assignment = _dispatch_command(
        session_id,
        'assign_session_role',
        {'peer_id': request.peer_id, 'role': request.role},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'session_role_assigned',
            {'peer_id': request.peer_id, 'role': request.role},
            revision=assignment.get('revision'),
        )
    return assignment


@router.post('/sessions/{session_id}/fog')
async def set_fog(session_id: str, request: FogRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(session_id, 'set_fog', {'enabled': request.enabled}, request.command)
    if not replay:
        await _publish_session_event(session_id, 'fog_changed', {'enabled': request.enabled}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/reveal-cell')
async def reveal_cell(session_id: str, request: RevealCellRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(session_id, 'reveal_cell', {'x': request.x, 'y': request.y}, request.command)
    if not replay:
        await _publish_session_event(session_id, 'cell_revealed', {'x': request.x, 'y': request.y}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/hide-cell')
async def hide_cell(session_id: str, request: HideCellRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(session_id, 'hide_cell', {'x': request.x, 'y': request.y}, request.command)
    if not replay:
        await _publish_session_event(session_id, 'cell_hidden', {'x': request.x, 'y': request.y}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/paint-terrain')
async def paint_terrain(session_id: str, request: PaintTerrainRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(
        session_id,
        'paint_terrain',
        {'x': request.x, 'y': request.y, 'terrain_type': request.terrain_type},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id, 'terrain_painted', {'x': request.x, 'y': request.y, 'terrain_type': request.terrain_type}, revision=state.get('revision')
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/toggle-blocked')
async def toggle_blocked(session_id: str, request: ToggleBlockedRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(session_id, 'toggle_blocked', {'x': request.x, 'y': request.y}, request.command)
    if not replay:
        await _publish_session_event(session_id, 'blocked_toggled', {'x': request.x, 'y': request.y}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/stamp-asset')
async def stamp_asset(session_id: str, request: StampAssetRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(
        session_id,
        'stamp_asset',
        {'x': request.x, 'y': request.y, 'asset_id': request.asset_id},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id, 'asset_stamped', {'x': request.x, 'y': request.y, 'asset_id': request.asset_id}, revision=state.get('revision')
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/recompute-visibility')
async def recompute_visibility(session_id: str, request: RecomputeVisibilityRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    state = _dispatch_command(
        session_id,
        'recompute_visibility',
        {'token_id': request.token_id, 'radius': request.radius},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'vision_updated',
            {'token_id': request.token_id, 'radius': request.radius},
            revision=state.get('revision'),
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/token-vision')
async def set_token_vision(session_id: str, request: TokenVisionRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    try:
        state = _dispatch_command(
            session_id,
            'set_token_vision_radius',
            {'token_id': request.token_id, 'radius': request.radius},
            request.command,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not replay:
        await _publish_session_event(
            session_id,
            'token_vision_updated',
            {'token_id': request.token_id, 'radius': request.radius},
            revision=state.get('revision'),
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/token-light')
async def set_token_light(session_id: str, request: TokenLightRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    try:
        state = _dispatch_command(
            session_id,
            'set_token_light',
            {
                'token_id': request.token_id,
                'bright_radius': request.bright_radius,
                'dim_radius': request.dim_radius,
                'color': request.color,
                'enabled': request.enabled,
            },
            request.command,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not replay:
        await _publish_session_event(
            session_id,
            'token_light_updated',
            {
                'token_id': request.token_id,
                'bright_radius': request.bright_radius,
                'dim_radius': request.dim_radius,
                'color': request.color,
                'enabled': request.enabled,
            },
            revision=state.get('revision'),
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/scene-lighting')
async def set_scene_lighting(session_id: str, request: SceneLightingRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    try:
        state = _dispatch_command(
            session_id,
            'set_scene_lighting',
            {'preset': request.preset},
            request.command,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not replay:
        await _publish_session_event(
            session_id,
            'scene_lighting_updated',
            {'preset': request.preset},
            revision=state.get('revision'),
        )
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/characters/import')
async def import_character(session_id: str, request: CharacterImportRequest) -> dict:
    replay = _is_idempotency_replay(session_id, request.command)
    try:
        result = _dispatch_command(
            session_id,
            'import_character',
            {'import_format': request.import_format, 'payload': request.payload, 'token_id': request.token_id},
            request.command,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not replay:
        await _publish_session_event(
            session_id, 'character_imported', {'token_id': result['token_id']}, revision=result.get('state', {}).get('revision')
        )
    return {'session_id': session_id, **result}


@router.get('/sessions/{session_id}/characters')
def list_characters(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _validate_read_identity(session_id, actor_peer_id, actor_token)
    characters = session_service.get_characters(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if characters is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'characters': characters}


@router.put('/sessions/{session_id}/notes')
def set_notes(session_id: str, request: SessionNotesRequest) -> dict:
    notes = _dispatch_command(session_id, 'set_notes', {'notes': request.notes}, request.command)
    return notes


@router.get('/sessions/{session_id}/notes')
def get_notes(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _validate_read_identity(session_id, actor_peer_id, actor_token)
    notes = session_service.get_notes(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if notes is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return notes


@router.post('/sessions/{session_id}/encounter-templates')
def add_template(session_id: str, request: EncounterTemplateRequest) -> dict:
    _require_command_identity(session_id, request.command)
    templates = _dispatch_command(
        session_id,
        'add_encounter_template',
        {'template_name': request.template_name, 'description': request.description},
        request.command,
    )
    return templates


@router.get('/sessions/{session_id}/journal-entries')
def list_journal_entries(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    entries = session_service.get_journal_entries(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if entries is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'journal_entries': entries}


@router.post('/sessions/{session_id}/journal-entries')
async def create_journal_entry(session_id: str, request: JournalEntryRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    entry = _dispatch_command(
        session_id,
        'create_journal_entry',
        {'title': request.title, 'content': request.content},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'journal_entry_created',
            {'entry_id': entry.get('entry', {}).get('entry_id')},
            revision=entry.get('revision'),
        )
    return entry


@router.put('/sessions/{session_id}/journal-entries/{entry_id}')
async def update_journal_entry(session_id: str, entry_id: str, request: JournalEntryUpdateRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    entry = _dispatch_command(
        session_id,
        'update_journal_entry',
        {'entry_id': entry_id, 'title': request.title, 'content': request.content},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'journal_entry_updated',
            {'entry_id': entry_id},
            revision=entry.get('revision'),
        )
    return entry


@router.post('/sessions/{session_id}/journal-entries/{entry_id}/share')
async def share_journal_entry(session_id: str, entry_id: str, request: ShareRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    entry = _dispatch_command(
        session_id,
        'share_journal_entry',
        {
            'entry_id': entry_id,
            'shared_roles': request.shared_roles,
            'shared_peer_ids': request.shared_peer_ids,
            'editable_roles': request.editable_roles,
            'editable_peer_ids': request.editable_peer_ids,
        },
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'journal_entry_shared',
            {'entry_id': entry_id},
            revision=entry.get('revision'),
        )
    return entry


@router.get('/sessions/{session_id}/handouts')
def list_handouts(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    handouts = session_service.get_handouts(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if handouts is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'handouts': handouts}


@router.post('/sessions/{session_id}/handouts')
async def create_handout(session_id: str, request: HandoutRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    handout = _dispatch_command(
        session_id,
        'create_handout',
        {'title': request.title, 'body': request.body},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'handout_created',
            {'handout_id': handout.get('handout', {}).get('handout_id')},
            revision=handout.get('revision'),
        )
    return handout


@router.put('/sessions/{session_id}/handouts/{handout_id}')
async def update_handout(session_id: str, handout_id: str, request: HandoutUpdateRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    handout = _dispatch_command(
        session_id,
        'update_handout',
        {'handout_id': handout_id, 'title': request.title, 'body': request.body},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'handout_updated',
            {'handout_id': handout_id},
            revision=handout.get('revision'),
        )
    return handout


@router.post('/sessions/{session_id}/handouts/{handout_id}/share')
async def share_handout(session_id: str, handout_id: str, request: ShareRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    handout = _dispatch_command(
        session_id,
        'share_handout',
        {
            'handout_id': handout_id,
            'shared_roles': request.shared_roles,
            'shared_peer_ids': request.shared_peer_ids,
            'editable_roles': request.editable_roles,
            'editable_peer_ids': request.editable_peer_ids,
        },
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'handout_shared',
            {'handout_id': handout_id},
            revision=handout.get('revision'),
        )
    return handout


@router.get('/sessions/{session_id}/assets')
def list_assets(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    assets = session_service.get_asset_library(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if assets is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'assets': assets}


@router.post('/sessions/{session_id}/assets')
async def add_asset_library_item(session_id: str, request: AssetLibraryItemRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    asset = _dispatch_command(
        session_id,
        'add_asset_library_item',
        {
            'asset_id': request.asset_id,
            'name': request.name,
            'asset_type': request.asset_type,
            'uri': request.uri,
            'tags': request.tags,
            'license': request.license,
        },
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'asset_library_item_added',
            {'asset_id': request.asset_id},
            revision=asset.get('revision'),
        )
    return asset


@router.get('/sessions/{session_id}/macros')
def list_macros(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    try:
        macros = session_service.get_macros(
            session_id,
            command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
        )
    except SessionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if macros is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'macros': macros}


@router.post('/sessions/{session_id}/macros')
async def create_macro(session_id: str, request: MacroRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    macro = _dispatch_command(
        session_id,
        'create_macro',
        {'name': request.name, 'template': request.template},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'macro_created',
            {'macro_id': macro.get('macro', {}).get('macro_id')},
            revision=macro.get('revision'),
        )
    return macro


@router.post('/sessions/{session_id}/macros/{macro_id}/run')
async def run_macro(session_id: str, macro_id: str, request: RunMacroRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    macro = _dispatch_command(
        session_id,
        'run_macro',
        {'macro_id': macro_id, 'variables': request.variables},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'macro_ran',
            {'macro_id': macro_id},
            revision=macro.get('revision'),
        )
    return macro


@router.get('/sessions/{session_id}/roll-templates')
def list_roll_templates(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    try:
        roll_templates = session_service.get_roll_templates(
            session_id,
            command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
        )
    except SessionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if roll_templates is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'roll_templates': roll_templates}


@router.post('/sessions/{session_id}/roll-templates')
async def create_roll_template(session_id: str, request: RollTemplateRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    roll_template = _dispatch_command(
        session_id,
        'create_roll_template',
        {'name': request.name, 'template': request.template, 'action_blocks': request.action_blocks},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'roll_template_created',
            {'roll_template_id': roll_template.get('roll_template', {}).get('roll_template_id')},
            revision=roll_template.get('revision'),
        )
    return roll_template


@router.post('/sessions/{session_id}/roll-templates/{roll_template_id}/render')
async def render_roll_template(session_id: str, roll_template_id: str, request: RenderRollTemplateRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    rendered = _dispatch_command(
        session_id,
        'render_roll_template',
        {'roll_template_id': roll_template_id, 'variables': request.variables},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'roll_template_rendered',
            {'roll_template_id': roll_template_id},
            revision=rendered.get('revision'),
        )
    return rendered


@router.get('/sessions/{session_id}/plugins')
def list_plugins(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    try:
        plugins = session_service.get_plugins(
            session_id,
            command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
        )
    except SessionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if plugins is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'plugins': plugins}


@router.post('/sessions/{session_id}/plugins')
async def register_plugin(session_id: str, request: PluginRequest) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    plugin = _dispatch_command(
        session_id,
        'register_plugin',
        {'name': request.name, 'version': request.version, 'capabilities': request.capabilities},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'plugin_registered',
            {'plugin_id': plugin.get('plugin', {}).get('plugin_id')},
            revision=plugin.get('revision'),
        )
    return plugin


@router.post('/sessions/{session_id}/plugins/{plugin_id}/hooks/{hook_name}/execute')
async def execute_plugin_hook(
    session_id: str,
    plugin_id: str,
    hook_name: str,
    request: ExecutePluginHookRequest,
) -> dict:
    _require_command_identity(session_id, request.command)
    replay = _is_idempotency_replay(session_id, request.command)
    result = _dispatch_command(
        session_id,
        'execute_plugin_hook',
        {'plugin_id': plugin_id, 'hook_name': hook_name, 'payload': request.payload},
        request.command,
    )
    if not replay:
        event_type = 'plugin_hook_failed' if result.get('status') == 'isolated_failure' else 'plugin_hook_succeeded'
        await _publish_session_event(
            session_id,
            event_type,
            {'plugin_id': plugin_id, 'hook_name': hook_name},
            revision=result.get('revision'),
        )
    return result


@router.get('/sessions/{session_id}/modules')
def list_modules(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    modules = session_service.list_modules(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if modules is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'modules': modules}


@router.post('/sessions/{session_id}/modules/install')
def install_module_pack(session_id: str, request: InstallPackRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='module install',
    )
    try:
        result = session_service.install_module_pack(
            session_id,
            manifest=request.manifest,
            checksum_sha256=request.checksum_sha256,
            signature_hmac_sha256=request.signature_hmac_sha256,
            command=_to_command_context(request.command),
        )
    except SessionPermissionError as exc:
        detail = str(exc)
        lowered = detail.lower()
        status_code = 400 if ('checksum' in lowered or 'signature' in lowered) else 403
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return result


@router.post('/sessions/{session_id}/modules/{module_id}/enable')
def enable_module(session_id: str, module_id: str, request: ToggleModuleRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='module toggle',
    )
    try:
        result = session_service.set_module_enabled(
            session_id,
            module_id=module_id,
            enabled=True,
            command=_to_command_context(request.command),
        )
    except SessionPermissionError as exc:
        raise HTTPException(status_code=404 if 'not found' in str(exc).lower() else 403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return result


@router.post('/sessions/{session_id}/modules/{module_id}/disable')
def disable_module(session_id: str, module_id: str, request: ToggleModuleRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='module toggle',
    )
    try:
        result = session_service.set_module_enabled(
            session_id,
            module_id=module_id,
            enabled=False,
            command=_to_command_context(request.command),
        )
    except SessionPermissionError as exc:
        raise HTTPException(status_code=404 if 'not found' in str(exc).lower() else 403, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return result


@router.get('/sessions/{session_id}/encounter-templates')
def get_templates(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    templates = session_service.get_encounter_templates(
        session_id,
        command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role),
    )
    if templates is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return templates


@router.post('/sessions/{session_id}/save')
def save_session(session_id: str) -> dict:
    path = session_service.save(session_id)
    if path is None:
        raise HTTPException(status_code=404, detail='Session not found')
    return {'session_id': session_id, 'saved_to': str(path)}


@router.post('/sessions/{session_id}/load')
def load_session(session_id: str) -> dict:
    state = session_service.load(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail='Saved session not found')
    return {'session_id': session_id, 'state': state}


@router.post('/sessions/{session_id}/migrate')
def migrate_session(session_id: str, request: MigrateSessionRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='migration operations',
    )
    result = session_service.migrate_session(session_id, dry_run=request.dry_run)
    if result is None:
        raise HTTPException(status_code=404, detail='Session not found')
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        action='session_migrated' if result.get('migrated') else 'session_migration_checked',
        detail={
            'dry_run': request.dry_run,
            'from_schema_version': result.get('from_schema_version'),
            'to_schema_version': result.get('to_schema_version'),
            'applied_migrations': result.get('applied_migrations', []),
        },
    )
    emit_ops_log(
        _ops_logger,
        event_type='session_migrated' if result.get('migrated') else 'session_migration_checked',
        session_id=session_id,
        actor_peer_id=request.command.actor_peer_id,
        detail={
            'dry_run': request.dry_run,
            'from_schema_version': result.get('from_schema_version'),
            'to_schema_version': result.get('to_schema_version'),
            'applied_migrations': result.get('applied_migrations', []),
        },
    )
    return result


@router.post('/sessions/{session_id}/backup')
def backup_session(session_id: str, request: BackupRequest | None = None) -> dict:
    _require_command_identity(session_id, request.command if request else None)
    assert request is not None and request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='backup operations',
    )
    _check_backup_rate_limit(session_id, request.command.actor_peer_id)
    backup = session_service.backup(session_id)
    if backup is None:
        raise HTTPException(status_code=404, detail='Session not found')
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        action='backup_created',
        detail={'backup_id': backup['backup_id']},
    )
    emit_ops_log(
        _ops_logger,
        event_type='backup_created',
        session_id=session_id,
        actor_peer_id=request.command.actor_peer_id,
        detail={'backup_id': backup['backup_id']},
    )
    return {'session_id': session_id, 'backup_id': backup['backup_id'], 'backup_path': str(backup['backup_path'])}


@router.post('/sessions/{session_id}/restore-backup')
def restore_session_backup(session_id: str, request: RestoreBackupRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='backup operations',
    )
    _check_backup_rate_limit(session_id, request.command.actor_peer_id)
    try:
        state = session_service.restore_backup(session_id, request.backup_id)
    except SessionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if state is None:
        raise HTTPException(status_code=404, detail='Backup not found')
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        action='backup_restored',
        detail={'backup_id': request.backup_id},
    )
    emit_ops_log(
        _ops_logger,
        event_type='backup_restored',
        session_id=session_id,
        actor_peer_id=request.command.actor_peer_id,
        detail={'backup_id': request.backup_id},
    )
    return {'session_id': session_id, 'state': state}


@router.get('/sessions/{session_id}/backups')
def list_session_backups(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    assert actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=actor_peer_id,
        actor_token=actor_token,
        actor_role=actor_role,
        operation_name='backup operations',
    )
    backups = session_service.list_backups(session_id)
    return {'session_id': session_id, 'backups': backups}


@router.post('/sessions/{session_id}/backups/prune')
def prune_session_backups(session_id: str, request: PruneBackupsRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='backup operations',
    )
    _check_backup_rate_limit(session_id, request.command.actor_peer_id)
    result = session_service.prune_backups(session_id, request.keep_latest)
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        action='backups_pruned',
        detail={'keep_latest': request.keep_latest, **result},
    )
    emit_ops_log(
        _ops_logger,
        event_type='backups_pruned',
        session_id=session_id,
        actor_peer_id=request.command.actor_peer_id,
        detail={'keep_latest': request.keep_latest, **result},
    )
    return {'session_id': session_id, **result}


@router.post('/sessions/{session_id}/backups/prune-by-age')
def prune_session_backups_by_age(session_id: str, request: PruneBackupsByAgeRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='backup operations',
    )
    _check_backup_rate_limit(session_id, request.command.actor_peer_id)
    result = session_service.prune_backups_by_age(session_id, request.max_age_days)
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        action='backups_pruned_by_age',
        detail={'max_age_days': request.max_age_days, **result},
    )
    emit_ops_log(
        _ops_logger,
        event_type='backups_pruned_by_age',
        session_id=session_id,
        actor_peer_id=request.command.actor_peer_id,
        detail={'max_age_days': request.max_age_days, **result},
    )
    return {'session_id': session_id, **result}


@router.get('/sessions/{session_id}/backups/{backup_id}/export')
def export_session_backup(
    session_id: str,
    backup_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    assert actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=actor_peer_id,
        actor_token=actor_token,
        actor_role=actor_role,
        operation_name='backup operations',
    )
    _check_backup_rate_limit(session_id, actor_peer_id)
    try:
        exported = session_service.export_backup(session_id, backup_id)
    except SessionPermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if exported is None:
        raise HTTPException(status_code=404, detail='Backup not found')
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=actor_peer_id,
        action='backup_exported',
        detail={'backup_id': backup_id},
    )
    emit_ops_log(
        _ops_logger,
        event_type='backup_exported',
        session_id=session_id,
        actor_peer_id=actor_peer_id,
        detail={'backup_id': backup_id},
    )
    return {'session_id': session_id, **exported}


@router.post('/sessions/{session_id}/backups/import')
def import_session_backup(session_id: str, request: ImportBackupRequest) -> dict:
    _require_command_identity(session_id, request.command)
    assert request.command is not None and request.command.actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        actor_token=request.command.actor_token,
        actor_role=request.command.actor_role,
        operation_name='backup operations',
    )
    _check_backup_rate_limit(session_id, request.command.actor_peer_id)
    try:
        imported = session_service.import_backup(
            session_id,
            request.backup,
            request.checksum_sha256,
            signature_hmac_sha256=request.signature_hmac_sha256,
        )
    except SessionPermissionError as exc:
        detail = str(exc)
        lowered = detail.lower()
        status_code = 400 if ('checksum' in lowered or 'too large' in lowered or 'signature' in lowered) else 403
        raise HTTPException(status_code=status_code, detail=detail) from exc
    _ops_state_store.record_backup_audit(
        session_id,
        actor_peer_id=request.command.actor_peer_id,
        action='backup_imported',
        detail={'backup_id': imported['backup_id']},
    )
    emit_ops_log(
        _ops_logger,
        event_type='backup_imported',
        session_id=session_id,
        actor_peer_id=request.command.actor_peer_id,
        detail={'backup_id': imported['backup_id']},
    )
    return {'session_id': session_id, 'backup_id': imported['backup_id'], 'backup_path': str(imported['backup_path'])}


@router.get('/sessions/{session_id}/backups/audit')
def list_backup_audit(
    session_id: str,
    actor_peer_id: str | None = Query(default=None),
    actor_token: str | None = Query(default=None),
    actor_role: str | None = Query(default=None),
) -> dict:
    _require_read_identity(session_id, actor_peer_id, actor_token)
    assert actor_peer_id is not None
    _require_privileged_gm_read(
        session_id,
        actor_peer_id=actor_peer_id,
        actor_token=actor_token,
        actor_role=actor_role,
        operation_name='backup operations',
    )
    audit = _ops_state_store.get_backup_audit(session_id)
    return {'session_id': session_id, 'audit': audit}


@router.get('/tutorial')
def get_tutorial() -> dict:
    return session_service.get_tutorial()


@router.post('/signal')
def signal(message: SignalMessage) -> dict:
    if not session_service.get_session(message.session_id):
        raise HTTPException(status_code=404, detail='Session not found')
    _message_bus.setdefault(message.target_id, []).append(message)
    return {'queued': True}


@router.get('/signal/{peer_id}')
def poll_signal(peer_id: str) -> dict:
    queued = _message_bus.pop(peer_id, [])
    return {'messages': [m.model_dump() for m in queued]}


@router.post('/relay-ticket')
def relay_ticket(request: RelayTicketRequest) -> dict:
    session = session_service.get_session(request.session_id)
    if not session or request.peer_id not in session.get('peers', []):
        raise HTTPException(status_code=404, detail='Session or peer not found')
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    return {
        'session_id': request.session_id,
        'peer_id': request.peer_id,
        'relay_token': secrets.token_urlsafe(24),
        'expires_at': expires_at.isoformat(),
    }


@router.websocket('/sessions/{session_id}/events')
async def session_events(
    session_id: str,
    websocket: WebSocket,
    actor_peer_id: str | None = None,
    actor_token: str | None = None,
    actor_role: str | None = None,
) -> None:
    if not actor_peer_id:
        await websocket.close(code=1008)
        return
    if not session_service.validate_peer_token(session_id, actor_peer_id, actor_token):
        await websocket.close(code=1008)
        return
    if not session_service.get_session(session_id, command=CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role)):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    connection_context = CommandContext(actor_peer_id=actor_peer_id, actor_role=actor_role)
    _ws_connections.setdefault(session_id, []).append((websocket, connection_context))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_connections[session_id] = [(ws, ctx) for ws, ctx in _ws_connections.get(session_id, []) if ws is not websocket]
