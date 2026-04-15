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
