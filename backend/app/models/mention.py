from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mentioned_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("collaboration_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    draft_review_id: Mapped[int | None] = mapped_column(
        ForeignKey("draft_reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    brand: Mapped["Brand"] = relationship(back_populates="mentions")
    author: Mapped["User"] = relationship(back_populates="authored_mentions", foreign_keys=[author_user_id])
    mentioned_user: Mapped["User"] = relationship(back_populates="received_mentions", foreign_keys=[mentioned_user_id])
    comment: Mapped["CollaborationComment | None"] = relationship(back_populates="mentions")
    draft_review: Mapped["DraftReview | None"] = relationship(back_populates="mentions")
