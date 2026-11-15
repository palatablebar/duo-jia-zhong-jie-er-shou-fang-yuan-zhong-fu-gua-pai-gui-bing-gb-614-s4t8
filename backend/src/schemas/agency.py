from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AgencyIn(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["broker", "platform", "feed"] = "broker"
    endpoint: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class AgencyPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    kind: Literal["broker", "platform", "feed"] | None = None
    endpoint: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    config: dict | None = None
    enabled: bool | None = None
