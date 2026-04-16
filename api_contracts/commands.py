from __future__ import annotations

from pydantic import BaseModel, Field


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


class SetFogCommand(BaseModel):
    enabled: bool


class RevealCellCommand(BaseModel):
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
