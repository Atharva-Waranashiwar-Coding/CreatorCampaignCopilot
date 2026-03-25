from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContentBriefBase(BaseModel):
    key_message: str | None = None
    call_to_action: str | None = None
    tone: str | None = None
    channels: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    references: str | None = None


class ContentBriefCreate(ContentBriefBase):
    pass


class ContentBriefUpdate(BaseModel):
    key_message: str | None = None
    call_to_action: str | None = None
    tone: str | None = None
    channels: list[str] | None = None
    themes: list[str] | None = None
    references: str | None = None


class ContentBriefRead(ContentBriefBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    created_at: datetime
    updated_at: datetime
