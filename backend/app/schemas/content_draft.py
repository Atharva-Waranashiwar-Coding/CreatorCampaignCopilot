from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DraftReviewAction, DraftStageType


class ContentDraftCreate(BaseModel):
    campaign_id: int
    title: str = Field(min_length=2, max_length=255)
    platform: str = Field(min_length=2, max_length=120)
    content_type: str = Field(min_length=2, max_length=120)
    content_body: str | None = None
    status: str | None = Field(default=None, min_length=2, max_length=80)
    planned_publish_at: datetime | None = None


class ContentDraftUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    platform: str | None = Field(default=None, min_length=2, max_length=120)
    content_type: str | None = Field(default=None, min_length=2, max_length=120)
    content_body: str | None = None
    status: str | None = Field(default=None, min_length=2, max_length=80)
    planned_publish_at: datetime | None = None


class ContentDraftStageMove(BaseModel):
    target_status: str = Field(min_length=2, max_length=80)
    comment: str | None = Field(default=None, max_length=5000)


class ContentDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    campaign_name: str
    project_id: int
    project_name: str
    brand_id: int
    brand_name: str
    title: str
    platform: str
    content_type: str
    content_body: str | None
    status: str
    status_label: str
    status_type: DraftStageType
    status_color: str
    planned_publish_at: datetime | None
    current_version_number: int
    created_by: int
    creator_name: str | None = None
    review_count: int = 0
    latest_review_action: DraftReviewAction | None = None
    latest_reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DraftWorkflowStageCount(BaseModel):
    status: str
    status_label: str
    status_type: DraftStageType
    count: int
