from __future__ import annotations

import json
import secrets
from asyncio import gather
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from api.schemas import (
    AssetLibraryItemRequest,
    ActorOwnershipRequest,
    ActorStateRequest,
    CharacterImportRequest,
    CommandContextRequest,
    EncounterTemplateRequest,
    FogRequest,
    InitiativeRequest,
    JoinRequest,
    MoveTokenRequest,
    NextTurnRequest,
    PaintTerrainRequest,
    PluginRequest,
    MacroRequest,
    RollTemplateRequest,
    RelayTicketRequest,
    RecomputeVisibilityRequest,
    TokenVisionRequest,
    RevealCellRequest,
    ShareRequest,
    SessionCreateRequest,
    JournalEntryRequest,
    JournalEntryUpdateRequest,
    HandoutRequest,
    HandoutUpdateRequest,
    SessionRoleRequest,
    SessionNotesRequest,
    SignalMessage,
    StampAssetRequest,
    ToggleBlockedRequest,
    RunMacroRequest,
    RenderRollTemplateRequest,
    ExecutePluginHookRequest,
)
from app.commands.dispatcher import CommandDispatcher, InvalidCommandPayloadError, UnknownCommandError
from app.events.file_event_log import JsonlEventLogSink
from app.events.publisher import SessionEvent, SessionEventPublisher
from app.services.session_service import CommandContext, SessionConflictError, SessionPermissionError, SessionService

router = APIRouter(prefix='/api', tags=['tabletop'])
session_service = SessionService()
command_dispatcher = CommandDispatcher(session_service)
_message_bus: dict[str, list[SignalMessage]] = {}
_ws_connections: dict[str, list[tuple[WebSocket, CommandContext]]] = {}
_event_log_sink = JsonlEventLogSink()
_event_publisher = SessionEventPublisher(sinks=[_event_log_sink])


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
        },
        request.command,
    )
    if not replay:
        await _publish_session_event(session_id, 'actor_updated', {'actor_id': request.actor_id}, revision=state.get('revision'))
    return {'session_id': session_id, 'state': state}


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
    state = _dispatch_command(
        session_id,
        'set_token_vision_radius',
        {'token_id': request.token_id, 'radius': request.radius},
        request.command,
    )
    if not replay:
        await _publish_session_event(
            session_id,
            'token_vision_updated',
            {'token_id': request.token_id, 'radius': request.radius},
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
