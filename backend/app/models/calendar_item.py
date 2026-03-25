from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CalendarItem(TimestampMixin, Base):
    __tablename__ = "calendar_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(120))
    item_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    brand: Mapped["Brand"] = relationship(back_populates="calendar_items")
    campaign: Mapped["Campaign"] = relationship(back_populates="calendar_items")
    draft: Mapped["ContentDraft | None"] = relationship(back_populates="calendar_item")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
