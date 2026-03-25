from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import BrandRole, DraftReviewAction, DraftStatus


class DraftReviewCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)


class DraftReviewDecision(BaseModel):
    comment: str | None = Field(default=None, max_length=5000)


class DraftReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    draft_id: int
    actor_user_id: int
    actor_name: str | None = None
    action: DraftReviewAction
    comment: str | None
    version_number: int
    from_status: DraftStatus | None = None
    to_status: DraftStatus | None = None
    created_at: datetime


class DraftReviewThreadRead(BaseModel):
    draft_id: int
    current_user_role: BrandRole
    available_actions: list[DraftReviewAction]
    reviews: list[DraftReviewRead]
