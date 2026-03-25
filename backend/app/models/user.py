from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    drafts: Mapped[list["ContentDraft"]] = relationship(back_populates="creator", lazy="selectin")
    draft_reviews: Mapped[list["DraftReview"]] = relationship(back_populates="actor", lazy="selectin")
    campaign_assets: Mapped[list["CampaignAsset"]] = relationship(lazy="selectin")
    draft_versions: Mapped[list["DraftVersion"]] = relationship(lazy="selectin")
    calendar_items: Mapped[list["CalendarItem"]] = relationship(lazy="selectin")
    content_templates: Mapped[list["ContentTemplate"]] = relationship(lazy="selectin")
    tool_usage_logs: Mapped[list["ToolUsageLog"]] = relationship(back_populates="actor", lazy="selectin")
