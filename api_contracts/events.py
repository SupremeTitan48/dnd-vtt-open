from pydantic import BaseModel, Field


class Position(BaseModel):
    x: int
    y: int


class TokenMoved(BaseModel):
    token_id: str = Field(min_length=1)
    position: Position


class CombatStateUpdated(BaseModel):
    active_actor_id: str
    round_number: int = Field(ge=1)


class ChatMessageEvent(BaseModel):
    message_id: str = Field(min_length=1)
    sender_peer_id: str | None = None
    kind: str = Field(min_length=1)
    content: str = Field(min_length=1)
    visibility_mode: str = Field(min_length=1)
    whisper_targets: list[str] = Field(default_factory=list)
