from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import AssignmentEntityType, AssignmentStatus


class AssignmentCreate(BaseModel):
    assignment_type: AssignmentEntityType | None = None
    assignee_user_id: int
    note: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None


class AssignmentUpdate(BaseModel):
    assignee_user_id: int | None = None
    note: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None
    status: AssignmentStatus | None = None


class AssignmentRead(BaseModel):
    id: int
    brand_id: int
    assignment_type: AssignmentEntityType
    campaign_id: int | None = None
    draft_id: int | None = None
    entity_id: int
    assignee_user_id: int
    assignee_name: str | None = None
    assignee_email: str | None = None
    assigned_by_user_id: int
    assigned_by_name: str | None = None
    note: str | None = None
    due_at: datetime | None = None
    status: AssignmentStatus
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
