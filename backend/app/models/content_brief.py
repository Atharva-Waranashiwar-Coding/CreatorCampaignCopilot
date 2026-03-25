from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class ContentBrief(TimestampMixin, Base):
    __tablename__ = "content_briefs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    key_message: Mapped[str | None] = mapped_column(Text)
    call_to_action: Mapped[str | None] = mapped_column(Text)
    tone: Mapped[str | None] = mapped_column(Text)
    channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    themes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reference_materials: Mapped[str | None] = mapped_column("references", Text)

    campaign: Mapped["Campaign"] = relationship(back_populates="brief")
