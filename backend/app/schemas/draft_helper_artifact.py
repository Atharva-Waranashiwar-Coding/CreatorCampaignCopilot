from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import HelperArtifactStatus, HelperArtifactType


class DraftHelperArtifactCreate(BaseModel):
    tool_name: str = Field(min_length=2, max_length=120)
    artifact_type: HelperArtifactType
    title: str = Field(min_length=2, max_length=255)
    summary: str | None = Field(default=None, max_length=5000)
    payload: dict[str, Any] = Field(default_factory=dict)
    status: HelperArtifactStatus = HelperArtifactStatus.SAVED
    source_tool_usage_log_id: int | None = Field(default=None, ge=1)


class DraftHelperArtifactUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    summary: str | None = Field(default=None, max_length=5000)
    payload: dict[str, Any] | None = None
    status: HelperArtifactStatus | None = None


class DraftHelperArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    draft_id: int
    tool_name: str
    artifact_type: HelperArtifactType
    title: str
    summary: str | None = None
    payload: dict[str, Any]
    status: HelperArtifactStatus
    source_tool_usage_log_id: int | None = None
    source_tool_created_at: datetime | None = None
    created_by: int
    creator_name: str | None = None
    created_at: datetime
    updated_at: datetime
