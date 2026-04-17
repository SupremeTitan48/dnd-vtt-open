from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from api_contracts.commands import (
    AddAssetLibraryItemCommand,
    CreateMacroCommand,
    ExecutePluginHookCommand,
    SendChatMessageCommand,
    HideCellCommand,
    CreateRollTemplateCommand,
    AssignActorOwnerCommand,
    AssignSessionRoleCommand,
    AddEncounterTemplateCommand,
    CreateHandoutCommand,
    CreateJournalEntryCommand,
    ImportCharacterCommand,
    MoveTokenCommand,
    NextTurnCommand,
    PaintTerrainCommand,
    RevealCellCommand,
    RecomputeVisibilityCommand,
    SetSceneLightingCommand,
    SetTokenLightCommand,
    SetTokenVisionRadiusCommand,
    ShareHandoutCommand,
    ShareJournalEntryCommand,
    SetFogCommand,
    SetInitiativeCommand,
    SetNotesCommand,
    StampAssetCommand,
    ToggleBlockedCommand,
    RunMacroCommand,
    RenderRollTemplateCommand,
    RegisterPluginCommand,
    SheetActionRollCommand,
    UpdateHandoutCommand,
    UpdateJournalEntryCommand,
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
            'hide_cell': self._handle_hide_cell,
            'paint_terrain': self._handle_paint_terrain,
            'toggle_blocked': self._handle_toggle_blocked,
            'stamp_asset': self._handle_stamp_asset,
            'recompute_visibility': self._handle_recompute_visibility,
            'set_token_vision_radius': self._handle_set_token_vision_radius,
            'set_token_light': self._handle_set_token_light,
            'set_scene_lighting': self._handle_set_scene_lighting,
            'import_character': self._handle_import_character,
            'set_notes': self._handle_set_notes,
            'add_encounter_template': self._handle_add_encounter_template,
            'assign_actor_owner': self._handle_assign_actor_owner,
            'assign_session_role': self._handle_assign_session_role,
            'create_journal_entry': self._handle_create_journal_entry,
            'update_journal_entry': self._handle_update_journal_entry,
            'share_journal_entry': self._handle_share_journal_entry,
            'create_handout': self._handle_create_handout,
            'update_handout': self._handle_update_handout,
            'share_handout': self._handle_share_handout,
            'add_asset_library_item': self._handle_add_asset_library_item,
            'create_macro': self._handle_create_macro,
            'run_macro': self._handle_run_macro,
            'create_roll_template': self._handle_create_roll_template,
            'render_roll_template': self._handle_render_roll_template,
            'register_plugin': self._handle_register_plugin,
            'execute_plugin_hook': self._handle_execute_plugin_hook,
            'roll_sheet_action': self._handle_roll_sheet_action,
            'send_chat_message': self._handle_send_chat_message,
        }
        self._contracts: dict[str, type[BaseModel]] = {
            'move_token': MoveTokenCommand,
            'set_initiative': SetInitiativeCommand,
            'next_turn': NextTurnCommand,
            'update_actor': UpdateActorCommand,
            'set_fog': SetFogCommand,
            'reveal_cell': RevealCellCommand,
            'hide_cell': HideCellCommand,
            'paint_terrain': PaintTerrainCommand,
            'toggle_blocked': ToggleBlockedCommand,
            'stamp_asset': StampAssetCommand,
            'recompute_visibility': RecomputeVisibilityCommand,
            'set_token_vision_radius': SetTokenVisionRadiusCommand,
            'set_token_light': SetTokenLightCommand,
            'set_scene_lighting': SetSceneLightingCommand,
            'import_character': ImportCharacterCommand,
            'set_notes': SetNotesCommand,
            'add_encounter_template': AddEncounterTemplateCommand,
            'assign_actor_owner': AssignActorOwnerCommand,
            'assign_session_role': AssignSessionRoleCommand,
            'create_journal_entry': CreateJournalEntryCommand,
            'update_journal_entry': UpdateJournalEntryCommand,
            'share_journal_entry': ShareJournalEntryCommand,
            'create_handout': CreateHandoutCommand,
            'update_handout': UpdateHandoutCommand,
            'share_handout': ShareHandoutCommand,
            'add_asset_library_item': AddAssetLibraryItemCommand,
            'create_macro': CreateMacroCommand,
            'run_macro': RunMacroCommand,
            'create_roll_template': CreateRollTemplateCommand,
            'render_roll_template': RenderRollTemplateCommand,
            'register_plugin': RegisterPluginCommand,
            'execute_plugin_hook': ExecutePluginHookCommand,
            'roll_sheet_action': SheetActionRollCommand,
            'send_chat_message': SendChatMessageCommand,
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
            armor_class=payload.get('armor_class'),
            max_hit_points=payload.get('max_hit_points'),
            current_hit_points=payload.get('current_hit_points'),
            concentration=payload.get('concentration'),
            saves=payload.get('saves'),
            skills=payload.get('skills'),
            spell_slots=payload.get('spell_slots'),
            inventory_add=payload.get('inventory_add'),
            inventory_remove=payload.get('inventory_remove'),
            command=command,
        )

    def _handle_set_fog(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.set_fog(session_id, payload['enabled'], command=command)

    def _handle_reveal_cell(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.reveal_cell(session_id, payload['x'], payload['y'], command=command)

    def _handle_hide_cell(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.hide_cell(session_id, payload['x'], payload['y'], command=command)

    def _handle_paint_terrain(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.paint_terrain(session_id, payload['x'], payload['y'], payload['terrain_type'], command=command)

    def _handle_toggle_blocked(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.toggle_blocked(session_id, payload['x'], payload['y'], command=command)

    def _handle_stamp_asset(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.stamp_asset(session_id, payload['x'], payload['y'], payload['asset_id'], command=command)

    def _handle_recompute_visibility(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.recompute_visibility(
            session_id,
            payload['token_id'],
            payload['radius'],
            command=command,
        )

    def _handle_set_token_vision_radius(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.set_token_vision_radius(
            session_id,
            payload['token_id'],
            payload['radius'],
            command=command,
        )

    def _handle_set_token_light(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.set_token_light(
            session_id,
            payload['token_id'],
            bright_radius=payload['bright_radius'],
            dim_radius=payload['dim_radius'],
            color=payload['color'],
            enabled=payload['enabled'],
            command=command,
        )

    def _handle_set_scene_lighting(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.set_scene_lighting(
            session_id,
            payload['preset'],
            command=command,
        )

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

    def _handle_create_journal_entry(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.create_journal_entry(session_id, payload['title'], payload['content'], command=command)

    def _handle_update_journal_entry(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.update_journal_entry(
            session_id,
            payload['entry_id'],
            payload['title'],
            payload['content'],
            command=command,
        )

    def _handle_share_journal_entry(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.share_journal_entry(
            session_id,
            payload['entry_id'],
            shared_roles=payload.get('shared_roles', []),
            shared_peer_ids=payload.get('shared_peer_ids', []),
            editable_roles=payload.get('editable_roles', []),
            editable_peer_ids=payload.get('editable_peer_ids', []),
            command=command,
        )

    def _handle_create_handout(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.create_handout(session_id, payload['title'], payload['body'], command=command)

    def _handle_update_handout(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.update_handout(
            session_id,
            payload['handout_id'],
            payload['title'],
            payload['body'],
            command=command,
        )

    def _handle_share_handout(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.share_handout(
            session_id,
            payload['handout_id'],
            shared_roles=payload.get('shared_roles', []),
            shared_peer_ids=payload.get('shared_peer_ids', []),
            editable_roles=payload.get('editable_roles', []),
            editable_peer_ids=payload.get('editable_peer_ids', []),
            command=command,
        )

    def _handle_add_asset_library_item(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.add_asset_library_item(
            session_id,
            payload['asset_id'],
            payload['name'],
            payload['asset_type'],
            payload['uri'],
            payload.get('tags', []),
            payload.get('license'),
            command=command,
        )

    def _handle_create_macro(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.create_macro(
            session_id,
            payload['name'],
            payload['template'],
            command=command,
        )

    def _handle_run_macro(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.run_macro(
            session_id,
            payload['macro_id'],
            payload.get('variables', {}),
            command=command,
        )

    def _handle_create_roll_template(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.create_roll_template(
            session_id,
            payload['name'],
            payload['template'],
            payload.get('action_blocks', {}),
            command=command,
        )

    def _handle_render_roll_template(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.render_roll_template(
            session_id,
            payload['roll_template_id'],
            payload.get('variables', {}),
            command=command,
        )

    def _handle_register_plugin(self, session_id: str, payload: dict[str, Any], command: CommandContext) -> dict[str, Any] | None:
        return self._session_service.register_plugin(
            session_id,
            payload['name'],
            payload['version'],
            payload.get('capabilities', []),
            command=command,
        )

    def _handle_execute_plugin_hook(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.execute_plugin_hook(
            session_id,
            payload['plugin_id'],
            payload['hook_name'],
            payload.get('payload', {}),
            command=command,
        )

    def _handle_roll_sheet_action(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.roll_sheet_action(
            session_id=session_id,
            actor_id=payload['actor_id'],
            action_type=payload['action_type'],
            action_key=payload['action_key'],
            advantage_mode=payload.get('advantage_mode', 'normal'),
            visibility_mode=payload.get('visibility_mode', 'public'),
            command=command,
        )

    def _handle_send_chat_message(
        self, session_id: str, payload: dict[str, Any], command: CommandContext
    ) -> dict[str, Any] | None:
        return self._session_service.send_chat_message(
            session_id=session_id,
            content=payload['content'],
            kind=payload.get('kind', 'ic'),
            visibility_mode=payload.get('visibility_mode', 'public'),
            whisper_targets=payload.get('whisper_targets', []),
            command=command,
        )
