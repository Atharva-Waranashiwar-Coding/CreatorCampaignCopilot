from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class DraftHelperArtifact(TimestampMixin, Base):
    __tablename__ = "draft_helper_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="saved", index=True)
    source_tool_usage_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("tool_usage_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    draft: Mapped["ContentDraft"] = relationship(back_populates="helper_artifacts")
    creator: Mapped["User"] = relationship(back_populates="helper_artifacts", foreign_keys=[created_by])
    source_tool_usage_log: Mapped["ToolUsageLog | None"] = relationship(back_populates="helper_artifacts")
