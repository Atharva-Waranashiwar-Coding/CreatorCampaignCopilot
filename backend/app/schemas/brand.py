from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import BrandRole
from app.schemas.draft_workflow import DraftWorkflowRead, DraftWorkflowWrite


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    tone_of_voice: str | None = None
    target_audience: str | None = None
    preferred_channels: list[str] = Field(default_factory=list)
    guidelines_summary: str | None = None
    draft_workflow: DraftWorkflowWrite | None = None


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    industry: str | None = Field(default=None, max_length=120)
    tone_of_voice: str | None = None
    target_audience: str | None = None
    preferred_channels: list[str] | None = None
    guidelines_summary: str | None = None
    draft_workflow: DraftWorkflowWrite | None = None


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    industry: str | None
    tone_of_voice: str | None
    target_audience: str | None
    preferred_channels: list[str]
    guidelines_summary: str | None
    draft_workflow: DraftWorkflowRead
    created_by: int
    created_at: datetime
    updated_at: datetime
    current_user_role: BrandRole
    membership_count: int = 0
    project_count: int = 0
    campaign_count: int = 0
