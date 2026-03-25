from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.mixins import TimestampMixin


class Plan(TimestampMixin, Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    monthly_price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    yearly_price_cents: Mapped[int | None] = mapped_column(Integer)
    limits_json: Mapped[dict[str, Any]] = mapped_column("limits", JSON, nullable=False, default=dict)
    features_json: Mapped[dict[str, Any]] = mapped_column("features", JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    subscriptions: Mapped[list["BrandSubscription"]] = relationship(
        back_populates="plan",
        lazy="selectin",
    )
