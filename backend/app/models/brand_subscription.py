from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PlanInterval, SubscriptionStatus
from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class BrandSubscription(TimestampMixin, Base):
    __tablename__ = "brand_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    brand_id: Mapped[int] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(
            SubscriptionStatus,
            name="subscription_status",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        index=True,
    )
    billing_interval: Mapped[PlanInterval] = mapped_column(
        SAEnum(
            PlanInterval,
            name="plan_interval",
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=PlanInterval.MONTHLY,
    )
    external_subscription_id: Mapped[str | None] = mapped_column(String(120))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    plan_snapshot_json: Mapped[dict[str, Any]] = mapped_column("plan_snapshot", JSON, nullable=False, default=dict)

    brand: Mapped["Brand"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions", lazy="selectin")
