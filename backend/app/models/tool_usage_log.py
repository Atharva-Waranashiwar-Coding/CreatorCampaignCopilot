from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ToolUsageLog(Base):
    __tablename__ = "tool_usage_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=True, index=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("content_drafts.id", ondelete="CASCADE"), nullable=True, index=True)
    target_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invocation_source: Mapped[str] = mapped_column(String(40), nullable=False, default="rest")
    was_successful: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    request_trace: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result_trace: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actor: Mapped["User"] = relationship(foreign_keys=[actor_user_id], back_populates="tool_usage_logs")
    brand: Mapped["Brand | None"] = relationship(back_populates="tool_usage_logs")
    helper_artifacts: Mapped[list["DraftHelperArtifact"]] = relationship(
        back_populates="source_tool_usage_log",
        lazy="selectin",
    )
