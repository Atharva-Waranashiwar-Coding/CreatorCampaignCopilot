from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampaignAssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    asset_type: str = Field(min_length=2, max_length=80)
    file_url: str = Field(min_length=1)
    thumbnail_url: str | None = None
    mime_type: str | None = Field(default=None, max_length=255)
    file_size_bytes: int | None = Field(default=None, ge=0)
    notes: str | None = None


class CampaignAssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    asset_type: str | None = Field(default=None, min_length=2, max_length=80)
    file_url: str | None = Field(default=None, min_length=1)
    thumbnail_url: str | None = None
    mime_type: str | None = Field(default=None, max_length=255)
    file_size_bytes: int | None = Field(default=None, ge=0)
    notes: str | None = None


class CampaignAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    name: str
    asset_type: str
    file_url: str
    thumbnail_url: str | None
    mime_type: str | None
    file_size_bytes: int | None
    notes: str | None
    created_by: int
    creator_name: str | None = None
    created_at: datetime
    updated_at: datetime
