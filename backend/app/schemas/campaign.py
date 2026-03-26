from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import CampaignStatus


class CampaignCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=2, max_length=255)
    objective: str | None = None
    audience: str | None = None
    campaign_type: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    status: CampaignStatus = CampaignStatus.PLANNING


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    objective: str | None = None
    audience: str | None = None
    campaign_type: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    status: CampaignStatus | None = None


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_name: str
    brand_id: int
    brand_name: str
    name: str
    objective: str | None
    audience: str | None
    campaign_type: str | None
    start_date: date | None
    end_date: date | None
    status: CampaignStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    brief_id: int | None = None
    draft_count: int = 0
