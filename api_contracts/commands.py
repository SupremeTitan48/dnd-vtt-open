from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

PROFICIENCY_TIERS = {'none', 'half_proficient', 'proficient', 'expertise', 'expert'}


class SkillTierValue(BaseModel):
    modifier: int = 0
    proficiency: str | int | float = 'none'

    @field_validator('proficiency')
    @classmethod
    def validate_proficiency(cls, value: str | int | float) -> str | int | float:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized not in PROFICIENCY_TIERS:
                raise ValueError(f'proficiency must be one of {sorted(PROFICIENCY_TIERS)} or numeric')
            return normalized
        return value


class MoveTokenCommand(BaseModel):
    token_id: str = Field(min_length=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class SetInitiativeCommand(BaseModel):
    order: list[str] = Field(min_length=1)


class NextTurnCommand(BaseModel):
    pass


class UpdateActorCommand(BaseModel):
    actor_id: str = Field(min_length=1)
    hit_points: int | None = Field(default=None, ge=0)
    add_item: str | None = None
    add_condition: str | None = None
    armor_class: int | None = Field(default=None, ge=0)
    max_hit_points: int | None = Field(default=None, ge=0)
    current_hit_points: int | None = Field(default=None, ge=0)
    concentration: bool | None = None
    saves: dict[str, int] | None = None
    skills: dict[str, SkillTierValue] | None = None
    spell_slots: dict[str, dict[str, int]] | None = None
    inventory_add: str | None = None
    inventory_remove: str | None = None


class SheetActionRollCommand(BaseModel):
    actor_id: str = Field(min_length=1)
    action_type: Literal["ability", "save", "skill", "attack", "spell"] = "ability"
    action_key: str = Field(min_length=1)
    advantage_mode: Literal["normal", "advantage", "disadvantage"] = "normal"
    visibility_mode: Literal["public", "private", "gm_only"] = "public"


class SendChatMessageCommand(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    kind: Literal["ic", "ooc", "emote", "system", "whisper", "roll"] = "ic"
    visibility_mode: Literal["public", "private", "gm_only"] = "public"
    whisper_targets: list[str] = Field(default_factory=list)


class SetFogCommand(BaseModel):
    enabled: bool


class RevealCellCommand(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class HideCellCommand(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class PaintTerrainCommand(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    terrain_type: str = Field(min_length=1)


class ToggleBlockedCommand(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class StampAssetCommand(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    asset_id: str = Field(min_length=1)


class RecomputeVisibilityCommand(BaseModel):
    token_id: str = Field(min_length=1)
    radius: int = Field(ge=0)


class SetTokenVisionRadiusCommand(BaseModel):
    token_id: str = Field(min_length=1)
    radius: int = Field(ge=0)


class SetTokenLightCommand(BaseModel):
    token_id: str = Field(min_length=1)
    bright_radius: int = Field(ge=0)
    dim_radius: int = Field(ge=0)
    color: str = Field(min_length=1)
    enabled: bool


class SetSceneLightingCommand(BaseModel):
    preset: str = Field(min_length=1)


class ImportCharacterCommand(BaseModel):
    import_format: str = Field(min_length=1)
    payload: str = Field(min_length=1)
    token_id: str | None = None


class SetNotesCommand(BaseModel):
    notes: str


class AddEncounterTemplateCommand(BaseModel):
    template_name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AssignActorOwnerCommand(BaseModel):
    actor_id: str = Field(min_length=1)
    peer_id: str = Field(min_length=1)


class AssignSessionRoleCommand(BaseModel):
    peer_id: str = Field(min_length=1)
    role: str = Field(min_length=1)


class CreateJournalEntryCommand(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class UpdateJournalEntryCommand(BaseModel):
    entry_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)


class ShareJournalEntryCommand(BaseModel):
    entry_id: str = Field(min_length=1)
    shared_roles: list[str] = Field(default_factory=list)
    shared_peer_ids: list[str] = Field(default_factory=list)
    editable_roles: list[str] = Field(default_factory=list)
    editable_peer_ids: list[str] = Field(default_factory=list)


class CreateHandoutCommand(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class UpdateHandoutCommand(BaseModel):
    handout_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class ShareHandoutCommand(BaseModel):
    handout_id: str = Field(min_length=1)
    shared_roles: list[str] = Field(default_factory=list)
    shared_peer_ids: list[str] = Field(default_factory=list)
    editable_roles: list[str] = Field(default_factory=list)
    editable_peer_ids: list[str] = Field(default_factory=list)


class AddAssetLibraryItemCommand(BaseModel):
    asset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    license: str | None = None


class CreateMacroCommand(BaseModel):
    name: str = Field(min_length=1)
    template: str = Field(min_length=1)


class RunMacroCommand(BaseModel):
    macro_id: str = Field(min_length=1)
    variables: dict[str, str] = Field(default_factory=dict)


class CreateRollTemplateCommand(BaseModel):
    name: str = Field(min_length=1)
    template: str = Field(min_length=1)
    action_blocks: dict[str, str] = Field(default_factory=dict)


class RenderRollTemplateCommand(BaseModel):
    roll_template_id: str = Field(min_length=1)
    variables: dict[str, str] = Field(default_factory=dict)


class RegisterPluginCommand(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)


class ExecutePluginHookCommand(BaseModel):
    plugin_id: str = Field(min_length=1)
    hook_name: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)
