from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContentTemplateCreate(BaseModel):
    brand_id: int
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    template_type: str = Field(min_length=2, max_length=80)
    platform: str | None = Field(default=None, max_length=120)
    content_type: str | None = Field(default=None, max_length=120)
    body: str = Field(min_length=2)


class ContentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    template_type: str | None = Field(default=None, min_length=2, max_length=80)
    platform: str | None = Field(default=None, max_length=120)
    content_type: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, min_length=2)


class ContentTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    brand_name: str
    name: str
    description: str | None
    template_type: str
    platform: str | None
    content_type: str | None
    body: str
    created_by: int
    creator_name: str | None
    created_at: datetime
    updated_at: datetime
