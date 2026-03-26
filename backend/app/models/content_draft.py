from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class ContentDraft(TimestampMixin, Base):
    __tablename__ = "content_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    content_body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(120), nullable=False, default="draft", index=True)
    planned_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="drafts")
    creator: Mapped["User"] = relationship(back_populates="drafts", foreign_keys=[created_by])
    reviews: Mapped[list["DraftReview"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DraftReview.created_at.desc()",
    )
    versions: Mapped[list["DraftVersion"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DraftVersion.version_number.desc()",
    )
    calendar_item: Mapped["CalendarItem | None"] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
    )
    comments: Mapped[list["CollaborationComment"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CollaborationComment.created_at.asc()",
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Assignment.created_at.desc()",
    )
    helper_artifacts: Mapped[list["DraftHelperArtifact"]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DraftHelperArtifact.updated_at.desc()",
    )
