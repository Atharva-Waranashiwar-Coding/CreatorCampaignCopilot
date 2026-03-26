from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import DraftStageType

_STAGE_KEY_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalize_stage_key(value: str) -> str:
    normalized = _STAGE_KEY_PATTERN.sub("_", value.strip().lower()).strip("_")
    if len(normalized) < 2:
        raise ValueError("Stage keys must include at least two letters or numbers.")
    return normalized


class DraftWorkflowStageBase(BaseModel):
    key: str = Field(min_length=2, max_length=80)
    label: str = Field(min_length=1, max_length=80)
    stage_type: DraftStageType
    color: str = Field(default="slate", min_length=2, max_length=40)
    description: str | None = Field(default=None, max_length=240)
    is_initial: bool = False
    allowed_next_stage_keys: list[str] = Field(default_factory=list)

    @field_validator("key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        return _normalize_stage_key(value)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("allowed_next_stage_keys")
    @classmethod
    def validate_allowed_next_stage_keys(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = _normalize_stage_key(value)
            if key in seen:
                continue
            normalized.append(key)
            seen.add(key)
        return normalized


class DraftWorkflowStageWrite(DraftWorkflowStageBase):
    pass


class DraftWorkflowStageRead(DraftWorkflowStageBase):
    model_config = ConfigDict(from_attributes=True)


class DraftWorkflowWrite(BaseModel):
    stages: list[DraftWorkflowStageWrite] = Field(min_length=1)


class DraftWorkflowRead(BaseModel):
    stages: list[DraftWorkflowStageRead]
    initial_stage_keys: list[str]
    review_stage_key: str
    approved_stage_key: str
    changes_requested_stage_key: str
    scheduled_stage_key: str | None = None
    published_stage_key: str
