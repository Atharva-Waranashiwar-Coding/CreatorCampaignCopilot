from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(120))
    tone_of_voice: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    preferred_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    guidelines_summary: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    memberships: Mapped[list["BrandMembership"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    calendar_items: Mapped[list["CalendarItem"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CalendarItem.scheduled_for.asc()",
    )
    subscription: Mapped["BrandSubscription | None"] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )
    templates: Mapped[list["ContentTemplate"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ContentTemplate.updated_at.desc()",
    )
    collaboration_comments: Mapped[list["CollaborationComment"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CollaborationComment.created_at.asc()",
    )
    mentions: Mapped[list["Mention"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Assignment.created_at.desc()",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Notification.created_at.desc()",
    )
    tool_usage_logs: Mapped[list["ToolUsageLog"]] = relationship(
        back_populates="brand",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ToolUsageLog.created_at.desc()",
    )
