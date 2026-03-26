from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ProjectStatus


class ProjectCreate(BaseModel):
    brand_id: int
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    brand_name: str
    name: str
    description: str | None
    status: ProjectStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    campaign_count: int = 0
