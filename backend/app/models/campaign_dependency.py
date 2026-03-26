from __future__ import annotations

from sqlalchemy import Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CampaignDependencyNodeType
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class CampaignDependency(TimestampMixin, Base):
    __tablename__ = "campaign_dependencies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependent_type: Mapped[CampaignDependencyNodeType] = mapped_column(
        SAEnum(CampaignDependencyNodeType, name="campaign_dependency_node_type", native_enum=False),
        nullable=False,
    )
    dependent_milestone_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaign_milestones.id", ondelete="CASCADE"),
        nullable=True,
    )
    dependent_draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=True,
    )
    dependent_stage_key: Mapped[str | None] = mapped_column(String(120))
    blocker_type: Mapped[CampaignDependencyNodeType] = mapped_column(
        SAEnum(CampaignDependencyNodeType, name="campaign_dependency_node_type", native_enum=False),
        nullable=False,
    )
    blocker_milestone_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaign_milestones.id", ondelete="CASCADE"),
        nullable=True,
    )
    blocker_draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=True,
    )
    blocker_stage_key: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="dependencies")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    dependent_milestone: Mapped["CampaignMilestone | None"] = relationship(
        foreign_keys=[dependent_milestone_id],
    )
    blocker_milestone: Mapped["CampaignMilestone | None"] = relationship(
        foreign_keys=[blocker_milestone_id],
    )
    dependent_draft: Mapped["ContentDraft | None"] = relationship(
        foreign_keys=[dependent_draft_id],
    )
    blocker_draft: Mapped["ContentDraft | None"] = relationship(
        foreign_keys=[blocker_draft_id],
    )
