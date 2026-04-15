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
