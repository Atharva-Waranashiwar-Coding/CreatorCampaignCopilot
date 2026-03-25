from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CampaignDependencyNodeType


class CampaignDependencyCreate(BaseModel):
    dependent_type: CampaignDependencyNodeType
    dependent_milestone_id: int | None = None
    dependent_draft_id: int | None = None
    dependent_stage_key: str | None = Field(default=None, min_length=2, max_length=120)
    blocker_type: CampaignDependencyNodeType
    blocker_milestone_id: int | None = None
    blocker_draft_id: int | None = None
    blocker_stage_key: str | None = Field(default=None, min_length=2, max_length=120)
    note: str | None = Field(default=None, max_length=5000)


class CampaignDependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    dependent_type: CampaignDependencyNodeType
    dependent_milestone_id: int | None
    dependent_draft_id: int | None
    dependent_stage_key: str | None
    dependent_label: str
    blocker_type: CampaignDependencyNodeType
    blocker_milestone_id: int | None
    blocker_draft_id: int | None
    blocker_stage_key: str | None
    blocker_label: str
    note: str | None
    created_by: int
    creator_name: str | None = None
    is_satisfied: bool
    created_at: datetime
    updated_at: datetime
