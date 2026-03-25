from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import DraftStatus


class DraftVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    draft_id: int
    draft_title: str
    campaign_id: int
    campaign_name: str
    project_id: int
    project_name: str
    brand_id: int
    brand_name: str
    version_number: int
    title: str
    platform: str
    content_type: str
    content_body: str | None
    status: DraftStatus
    planned_publish_at: datetime | None
    change_summary: str | None
    created_by: int
    creator_name: str | None = None
    created_at: datetime
