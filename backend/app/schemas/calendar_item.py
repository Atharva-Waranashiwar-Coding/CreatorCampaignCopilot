from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CalendarItemCreate(BaseModel):
    campaign_id: int
    title: str = Field(min_length=2, max_length=255)
    platform: str | None = Field(default=None, max_length=120)
    item_type: str = Field(min_length=2, max_length=80)
    scheduled_for: datetime
    status: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class CalendarItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    platform: str | None = Field(default=None, max_length=120)
    item_type: str | None = Field(default=None, min_length=2, max_length=80)
    scheduled_for: datetime | None = None
    status: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class CalendarItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    brand_name: str
    campaign_id: int
    campaign_name: str
    draft_id: int | None
    draft_title: str | None = None
    title: str
    platform: str | None
    item_type: str
    scheduled_for: datetime
    status: str | None
    notes: str | None
    created_by: int
    creator_name: str | None = None
    created_at: datetime
    updated_at: datetime
