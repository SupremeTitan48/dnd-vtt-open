from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from api_contracts.commands import (
    AssignActorOwnerCommand,
    AssignSessionRoleCommand,
    AddEncounterTemplateCommand,
    ImportCharacterCommand,
    MoveTokenCommand,
    NextTurnCommand,
    PaintTerrainCommand,
    RevealCellCommand,
    SetFogCommand,
    SetInitiativeCommand,
    SetNotesCommand,
    StampAssetCommand,
    ToggleBlockedCommand,
    UpdateActorCommand,
)
from app.services.session_service import CommandContext, SessionService


class UnknownCommandError(Exception):
    pass


class InvalidCommandPayloadError(Exception):
    pass


class CommandDispatcher:
    def __init__(self, session_service: SessionService):
        self._session_service = session_service
        self._handlers: dict[str, Callable[[str, dict[str, Any], CommandContext], dict[str, Any] | None]] = {
            'move_token': self._handle_move_token,
            'set_initiative': self._handle_set_initiative,
            'next_turn': self._handle_next_turn,
            'update_actor': self._handle_update_actor,
            'set_fog': self._handle_set_fog,
            'reveal_cell': self._handle_reveal_cell,
            'paint_terrain': self._handle_paint_terrain,
            'toggle_blocked': self._handle_toggle_blocked,
            'stamp_asset': self._handle_stamp_asset,
            'import_character': self._handle_import_character,
            'set_notes': self._handle_set_notes,
            'add_encounter_template': self._handle_add_encounter_template,
            'assign_actor_owner': self._handle_assign_actor_owner,
            'assign_session_role': self._handle_assign_session_role,
        }
        self._contracts: dict[str, type[BaseModel]] = {
            'move_token': MoveTokenCommand,
            'set_initiative': SetInitiativeCommand,
            'next_turn': NextTurnCommand,
            'update_actor': UpdateActorCommand,
            'set_fog': SetFogCommand,
            'reveal_cell': RevealCellCommand,
            'paint_terrain': PaintTerrainCommand,
            'toggle_blocked': ToggleBlockedCommand,
            'stamp_asset': StampAssetCommand,
            'import_character': ImportCharacterCommand,
            'set_notes': SetNotesCommand,
            'add_encounter_template': AddEncounterTemplateCommand,
            'assign_actor_owner': AssignActorOwnerCommand,
            'assign_session_role': AssignSessionRoleCommand,
        }

    def dispatch(self, session_id: str, action: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        handler = self._handlers.get(action)
        if handler is None:
            raise UnknownCommandError(f'Unknown command action: {action}')
        validated_payload = self._validate_payload(action, payload)
        return handler(session_id, validated_payload, command)

    def _validate_payload(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        contract = self._contracts.get(action)
        if contract is None:
            raise UnknownCommandError(f'No command contract registered for action: {action}')
        try:
            return contract.model_validate(payload).model_dump()
        except ValidationError as exc:
            raise InvalidCommandPayloadError(str(exc)) from exc

    def _handle_move_token(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.move_token(
            session_id,
            payload['token_id'],
            payload['x'],
            payload['y'],
            command=command,
        )

    def _handle_set_initiative(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.set_initiative(session_id, payload['order'], command=command)

    def _handle_next_turn(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        del payload
        return self._session_service.next_turn(session_id, command=command)

    def _handle_update_actor(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.update_actor(
            session_id=session_id,
            actor_id=payload['actor_id'],
            hit_points=payload.get('hit_points'),
            add_item=payload.get('add_item'),
            add_condition=payload.get('add_condition'),
            command=command,
        )

    def _handle_set_fog(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.set_fog(session_id, payload['enabled'], command=command)

    def _handle_reveal_cell(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.reveal_cell(session_id, payload['x'], payload['y'], command=command)

    def _handle_paint_terrain(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.paint_terrain(session_id, payload['x'], payload['y'], payload['terrain_type'], command=command)

    def _handle_toggle_blocked(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.toggle_blocked(session_id, payload['x'], payload['y'], command=command)

    def _handle_stamp_asset(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.stamp_asset(session_id, payload['x'], payload['y'], payload['asset_id'], command=command)

    def _handle_import_character(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.import_character(
            session_id,
            payload['import_format'],
            payload['payload'],
            payload.get('token_id'),
            command=command,
        )

    def _handle_set_notes(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.set_notes(session_id, payload['notes'], command=command)

    def _handle_add_encounter_template(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.add_encounter_template(
            session_id,
            payload['template_name'],
            payload['description'],
            command=command,
        )

    def _handle_assign_actor_owner(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.assign_actor_owner(
            session_id,
            payload['actor_id'],
            payload['peer_id'],
            command=command,
        )

    def _handle_assign_session_role(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.assign_session_role(
            session_id,
            payload['peer_id'],
            payload['role'],
            command=command,
        )
