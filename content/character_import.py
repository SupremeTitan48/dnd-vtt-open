from __future__ import annotations

import csv
import io
import json
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, model_validator


class CharacterSheet(BaseModel):
    name: str = Field(min_length=1)
    character_class: str = Field(min_length=1)
    level: int = Field(ge=1)
    hit_points: int = Field(ge=1)
    items: list[str] = []
    saves: dict[str, int] = {}
    skills: dict[str, dict[str, int | str]] = {}
    armor_class: int = Field(default=10, ge=0)
    max_hit_points: int = Field(default=1, ge=1)
    current_hit_points: int = Field(default=1, ge=0)
    concentration: bool = False
    spell_slots: dict[str, dict[str, int]] = {}

    @model_validator(mode="after")
    def sync_hp_fields(self) -> "CharacterSheet":
        if self.max_hit_points <= 1:
            self.max_hit_points = self.hit_points
        if self.current_hit_points <= 1:
            self.current_hit_points = self.hit_points
        self.current_hit_points = max(0, min(self.current_hit_points, self.max_hit_points))
        return self


def normalize_character(data: dict) -> CharacterSheet:
    return CharacterSheet.model_validate(data)


def validate_character_or_errors(data: dict) -> tuple[Optional[CharacterSheet], list[str]]:
    try:
        return normalize_character(data), []
    except ValidationError as exc:
        return None, [err["msg"] for err in exc.errors()]


def import_json(payload: str) -> CharacterSheet:
    return normalize_character(json.loads(payload))


def import_dndbeyond_json(payload: str) -> CharacterSheet:
    raw = json.loads(payload)
    mapped = {
        "name": raw.get("name") or raw.get("characterName") or "Unknown",
        "character_class": raw.get("character_class")
        or raw.get("class")
        or raw.get("classes", [{}])[0].get("name", "Adventurer"),
        "level": raw.get("level") or raw.get("classes", [{}])[0].get("level", 1),
        "hit_points": raw.get("hit_points")
        or raw.get("baseHitPoints")
        or raw.get("currentHp")
        or 1,
        "items": raw.get("items")
        or [item.get("name", "Item") for item in raw.get("inventory", []) if isinstance(item, dict)],
    }
    return normalize_character(mapped)


def import_csv(payload: str) -> CharacterSheet:
    reader = csv.DictReader(io.StringIO(payload))
    first = next(reader)
    mapped = {
        "name": first.get("name", "Unknown"),
        "character_class": first.get("character_class") or first.get("class") or "Adventurer",
        "level": int(first.get("level", "1")),
        "hit_points": int(first.get("hit_points", "1")),
        "items": [i.strip() for i in (first.get("items", "")).split(";") if i.strip()],
    }
    return normalize_character(mapped)


def import_pdf_best_effort(payload: str) -> CharacterSheet:
    # Best effort text parser (payload is extracted text from PDF client/tool)
    lines = [line.strip() for line in payload.splitlines() if line.strip()]
    data: dict[str, str] = {}
    for line in lines:
        lower = line.lower()
        if lower.startswith("name:"):
            data["name"] = line.split(":", 1)[1].strip()
        elif lower.startswith("class:"):
            data["character_class"] = line.split(":", 1)[1].strip()
        elif lower.startswith("level:"):
            data["level"] = line.split(":", 1)[1].strip()
        elif lower.startswith("hp:") or lower.startswith("hit points:"):
            data["hit_points"] = line.split(":", 1)[1].strip()
        elif lower.startswith("items:"):
            data["items"] = line.split(":", 1)[1].strip()

    mapped = {
        "name": data.get("name", "Unknown"),
        "character_class": data.get("character_class", "Adventurer"),
        "level": int(data.get("level", "1")),
        "hit_points": int(data.get("hit_points", "1")),
        "items": [i.strip() for i in data.get("items", "").split(",") if i.strip()],
    }
    return normalize_character(mapped)


def import_character_by_format(import_format: str, payload: str) -> CharacterSheet:
    normalized = import_format.lower()
    if normalized == "json_schema":
        return import_json(payload)
    if normalized == "dndbeyond_json":
        return import_dndbeyond_json(payload)
    if normalized == "csv_basic":
        return import_csv(payload)
    if normalized == "pdf_parse":
        return import_pdf_best_effort(payload)
    raise ValueError(f"Unsupported import format: {import_format}")
