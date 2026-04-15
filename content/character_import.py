from pydantic import BaseModel, Field, ValidationError
from typing import Optional


class CharacterSheet(BaseModel):
    name: str = Field(min_length=1)
    character_class: str = Field(min_length=1)
    level: int = Field(ge=1)
    hit_points: int = Field(ge=1)
    items: list[str] = []


def normalize_character(data: dict) -> CharacterSheet:
    return CharacterSheet.model_validate(data)


def validate_character_or_errors(data: dict) -> tuple[Optional[CharacterSheet], list[str]]:
    try:
        return normalize_character(data), []
    except ValidationError as exc:
        return None, [err["msg"] for err in exc.errors()]
