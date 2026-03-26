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
    authored_comments: Mapped[list["CollaborationComment"]] = relationship(
        back_populates="author",
        lazy="selectin",
        foreign_keys="CollaborationComment.author_user_id",
    )
    authored_mentions: Mapped[list["Mention"]] = relationship(
        back_populates="author",
        lazy="selectin",
        foreign_keys="Mention.author_user_id",
    )
    received_mentions: Mapped[list["Mention"]] = relationship(
        back_populates="mentioned_user",
        lazy="selectin",
        foreign_keys="Mention.mentioned_user_id",
    )
    created_assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="assigned_by",
        lazy="selectin",
        foreign_keys="Assignment.assigned_by_user_id",
    )
    received_assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="assignee",
        lazy="selectin",
        foreign_keys="Assignment.assignee_user_id",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        lazy="selectin",
        foreign_keys="Notification.user_id",
    )
    triggered_notifications: Mapped[list["Notification"]] = relationship(
        back_populates="actor",
        lazy="selectin",
        foreign_keys="Notification.actor_user_id",
    )
    tool_usage_logs: Mapped[list["ToolUsageLog"]] = relationship(back_populates="actor", lazy="selectin")
    helper_artifacts: Mapped[list["DraftHelperArtifact"]] = relationship(
        back_populates="creator",
        lazy="selectin",
    )
