from __future__ import annotations

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CommentEntityType
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CollaborationComment(TimestampMixin, Base):
    __tablename__ = "collaboration_comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[CommentEntityType] = mapped_column(
        SAEnum(CommentEntityType, name="comment_entity_type", native_enum=False),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=True, index=True)
    parent_comment_id: Mapped[int | None] = mapped_column(
        ForeignKey("collaboration_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    brand: Mapped["Brand"] = relationship(back_populates="collaboration_comments")
    campaign: Mapped["Campaign | None"] = relationship(back_populates="comments")
    draft: Mapped["ContentDraft | None"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="authored_comments", foreign_keys=[author_user_id])
    parent_comment: Mapped["CollaborationComment | None"] = relationship(
        remote_side=[id],
        back_populates="replies",
    )
    replies: Mapped[list["CollaborationComment"]] = relationship(
        back_populates="parent_comment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CollaborationComment.created_at.asc()",
    )
    mentions: Mapped[list["Mention"]] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
