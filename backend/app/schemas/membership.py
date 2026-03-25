from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.enums import BrandRole, MembershipStatus
from app.schemas.user import UserRead


class MembershipInviteRequest(BaseModel):
    email: EmailStr
    role: BrandRole


class MembershipUpdate(BaseModel):
    role: BrandRole | None = None
    status: MembershipStatus | None = None


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    user_id: int | None
    invite_email: EmailStr
    invited_by_id: int | None
    role: BrandRole
    status: MembershipStatus
    invited_at: datetime
    joined_at: datetime | None
    created_at: datetime
    updated_at: datetime
    user: UserRead | None = None
