from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CampaignMilestoneKey
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CampaignMilestone(TimestampMixin, Base):
    __tablename__ = "campaign_milestones"
    __table_args__ = (
        UniqueConstraint("campaign_id", "key", name="uq_campaign_milestones_campaign_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[CampaignMilestoneKey] = mapped_column(
        SAEnum(CampaignMilestoneKey, name="campaign_milestone_key", native_enum=False),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    campaign: Mapped["Campaign"] = relationship(back_populates="milestones")
    completed_by: Mapped["User | None"] = relationship(foreign_keys=[completed_by_user_id])
