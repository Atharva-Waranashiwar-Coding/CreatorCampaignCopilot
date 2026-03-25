from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import DraftReviewAction
from app.db.base_class import Base


class DraftReview(Base):
    __tablename__ = "draft_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[DraftReviewAction] = mapped_column(
        SAEnum(DraftReviewAction, name="draft_review_action", native_enum=False),
        nullable=False,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    from_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    draft: Mapped["ContentDraft"] = relationship(back_populates="reviews")
    actor: Mapped["User"] = relationship(back_populates="draft_reviews", foreign_keys=[actor_user_id])
    mentions: Mapped[list["Mention"]] = relationship(
        back_populates="draft_review",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
