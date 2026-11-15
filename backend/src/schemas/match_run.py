from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunIn(BaseModel):
    trigger: Literal["manual", "schedule", "seed"] = "manual"
    threshold: float = Field(default=0.80, ge=0.50, le=1.00)
    note: str | None = Field(default=None, max_length=200)
