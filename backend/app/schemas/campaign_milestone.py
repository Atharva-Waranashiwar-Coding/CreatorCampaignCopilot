from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CampaignMilestoneKey


class CampaignMilestoneUpdate(BaseModel):
    target_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_complete: bool | None = None


class CampaignMilestoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    key: CampaignMilestoneKey
    label: str
    sort_order: int
    target_date: date | None
    completed_at: datetime | None
    completed_by_user_id: int | None
    completed_by_name: str | None = None
    is_complete: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
