from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AssignmentEntityType, AssignmentStatus
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Assignment(TimestampMixin, Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_type: Mapped[AssignmentEntityType] = mapped_column(
        SAEnum(AssignmentEntityType, name="assignment_entity_type", native_enum=False),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    assignee_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus, name="assignment_status", native_enum=False),
        nullable=False,
        default=AssignmentStatus.OPEN,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    brand: Mapped["Brand"] = relationship(back_populates="assignments")
    campaign: Mapped["Campaign | None"] = relationship(back_populates="assignments")
    draft: Mapped["ContentDraft | None"] = relationship(back_populates="assignments")
    assignee: Mapped["User"] = relationship(back_populates="received_assignments", foreign_keys=[assignee_user_id])
    assigned_by: Mapped["User"] = relationship(back_populates="created_assignments", foreign_keys=[assigned_by_user_id])
