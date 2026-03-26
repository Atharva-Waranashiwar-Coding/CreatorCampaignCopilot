from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import BrandRole, MembershipStatus
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class BrandMembership(TimestampMixin, Base):
    __tablename__ = "brand_memberships"
    __table_args__ = (
        UniqueConstraint("brand_id", "invite_email", name="uq_brand_memberships_brand_invite_email"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    invite_email: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    role: Mapped[BrandRole] = mapped_column(
        SAEnum(BrandRole, name="brand_role", native_enum=False),
        nullable=False,
    )
    status: Mapped[MembershipStatus] = mapped_column(
        SAEnum(MembershipStatus, name="membership_status", native_enum=False),
        nullable=False,
        default=MembershipStatus.INVITED,
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    brand: Mapped["Brand"] = relationship(back_populates="memberships")
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])
    invited_by: Mapped["User | None"] = relationship(foreign_keys=[invited_by_id])
