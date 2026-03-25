from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.core.enums import NotificationType


class NotificationRead(BaseModel):
    id: int
    user_id: int
    brand_id: int
    actor_user_id: int | None = None
    actor_name: str | None = None
    notification_type: NotificationType
    title: str
    body: str
    entity_type: str
    entity_id: int | None = None
    metadata: dict[str, Any]
    read_at: datetime | None = None
    created_at: datetime


class NotificationSummaryRead(BaseModel):
    unread_count: int
    recent_unread: list[NotificationRead]


class NotificationMarkAllRead(BaseModel):
    updated_count: int
