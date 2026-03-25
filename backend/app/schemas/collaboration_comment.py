from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import CommentEntityType


class MentionRead(BaseModel):
    id: int
    mentioned_user_id: int
    mentioned_user_name: str
    mentioned_user_email: str
    identifier: str
    created_at: datetime


class CollaborationCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    parent_comment_id: int | None = None


class CollaborationCommentRead(BaseModel):
    id: int
    brand_id: int
    entity_type: CommentEntityType
    entity_id: int
    campaign_id: int | None = None
    draft_id: int | None = None
    parent_comment_id: int | None = None
    author_user_id: int
    author_name: str | None = None
    body: str
    mentions: list[MentionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    replies: list["CollaborationCommentRead"] = Field(default_factory=list)


CollaborationCommentRead.model_rebuild()
