from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PackResourceRef(BaseModel):
    resource_id: str = Field(min_length=1)
    operation: str = Field(default='upsert', min_length=1)


class PackPluginMetadata(BaseModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    capabilities: list[str] = Field(default_factory=list)


class InstallablePackManifest(BaseModel):
    pack_id: str = Field(min_length=1)
    pack_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = ''
    requires: list[str] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    actors: list[dict[str, Any]] = Field(default_factory=list)
    journals: list[dict[str, Any]] = Field(default_factory=list)
    handouts: list[dict[str, Any]] = Field(default_factory=list)
    macros: list[dict[str, Any]] = Field(default_factory=list)
    templates: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    plugins: list[PackPluginMetadata] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

