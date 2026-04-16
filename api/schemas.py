from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class CommandContextRequest(BaseModel):
    actor_peer_id: Optional[str] = None
    actor_token: Optional[str] = None
    actor_role: Optional[str] = None
    expected_revision: Optional[int] = Field(default=None, ge=0)
    idempotency_key: Optional[str] = Field(default=None, min_length=1)


class SessionCreateRequest(BaseModel):
    session_name: str = Field(min_length=1)
    host_peer_id: str = Field(min_length=1)
    campaign_id: Optional[str] = None
    map_width: int = Field(default=30, ge=5, le=200)
    map_height: int = Field(default=20, ge=5, le=200)


class JoinRequest(BaseModel):
    peer_id: str = Field(min_length=1)


class SignalMessage(BaseModel):
    session_id: str
    sender_id: str
    target_id: str
    payload: Dict[str, Any]


class RelayTicketRequest(BaseModel):
    session_id: str
    peer_id: str


class MoveTokenRequest(BaseModel):
    token_id: str = Field(min_length=1)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    command: Optional[CommandContextRequest] = None


class InitiativeRequest(BaseModel):
    order: List[str] = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class NextTurnRequest(BaseModel):
    command: Optional[CommandContextRequest] = None


class ActorStateRequest(BaseModel):
    actor_id: str = Field(min_length=1)
    hit_points: Optional[int] = Field(default=None, ge=0)
    add_item: Optional[str] = None
    add_condition: Optional[str] = None
    command: Optional[CommandContextRequest] = None


class ActorOwnershipRequest(BaseModel):
    actor_id: str = Field(min_length=1)
    peer_id: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class SessionRoleRequest(BaseModel):
    peer_id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class FogRequest(BaseModel):
    enabled: bool
    command: Optional[CommandContextRequest] = None


class RevealCellRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    command: Optional[CommandContextRequest] = None


class PaintTerrainRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    terrain_type: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class ToggleBlockedRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    command: Optional[CommandContextRequest] = None


class StampAssetRequest(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    asset_id: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class RecomputeVisibilityRequest(BaseModel):
    token_id: str = Field(min_length=1)
    radius: int = Field(ge=0)
    command: Optional[CommandContextRequest] = None


class TokenVisionRequest(BaseModel):
    token_id: str = Field(min_length=1)
    radius: int = Field(ge=0)
    command: Optional[CommandContextRequest] = None


class CharacterImportRequest(BaseModel):
    import_format: str
    payload: str
    token_id: Optional[str] = None
    command: Optional[CommandContextRequest] = None


class SessionNotesRequest(BaseModel):
    notes: str
    command: Optional[CommandContextRequest] = None


class EncounterTemplateRequest(BaseModel):
    template_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class JournalEntryRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class JournalEntryUpdateRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class ShareRequest(BaseModel):
    shared_roles: List[str] = Field(default_factory=list)
    shared_peer_ids: List[str] = Field(default_factory=list)
    editable_roles: List[str] = Field(default_factory=list)
    editable_peer_ids: List[str] = Field(default_factory=list)
    command: Optional[CommandContextRequest] = None


class HandoutRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class HandoutUpdateRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    command: Optional[CommandContextRequest] = None


class AssetLibraryItemRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    asset_type: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    tags: List[str] = Field(default_factory=list)
    license: Optional[str] = None
    command: Optional[CommandContextRequest] = None


class MacroRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    template: str = Field(min_length=1, max_length=1000)
    command: Optional[CommandContextRequest] = None


class RunMacroRequest(BaseModel):
    variables: Dict[str, str] = Field(default_factory=dict, max_length=32)
    command: Optional[CommandContextRequest] = None


class RollTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    template: str = Field(min_length=1, max_length=1000)
    action_blocks: Dict[str, str] = Field(default_factory=dict, max_length=32)
    command: Optional[CommandContextRequest] = None


class RenderRollTemplateRequest(BaseModel):
    variables: Dict[str, str] = Field(default_factory=dict, max_length=32)
    command: Optional[CommandContextRequest] = None


class PluginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=40)
    capabilities: List[str] = Field(default_factory=list, max_length=32)
    command: Optional[CommandContextRequest] = None

    @field_validator('capabilities')
    @classmethod
    def validate_capabilities(cls, capabilities: List[str]) -> List[str]:
        for capability in capabilities:
            if ':' not in capability:
                raise ValueError('capability must be in "domain:action" format')
            domain, action = capability.split(':', 1)
            if not domain.strip() or not action.strip():
                raise ValueError('capability must be in "domain:action" format')
        return capabilities


class ExecutePluginHookRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict, max_length=32)
    command: Optional[CommandContextRequest] = None
