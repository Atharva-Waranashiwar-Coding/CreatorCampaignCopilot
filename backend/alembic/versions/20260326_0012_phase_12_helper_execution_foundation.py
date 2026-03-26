"""phase 12 helper execution foundation

Revision ID: 20260326_0012
Revises: 20260325_0011
Create Date: 2026-03-26 11:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260326_0012"
down_revision = "20260325_0011"
branch_labels = None
depends_on = None


plans_table = sa.table(
    "plans",
    sa.column("code", sa.String()),
    sa.column("features", sa.JSON()),
    sa.column("limits", sa.JSON()),
)


def _updated_features(code: str, existing: dict[str, object] | None) -> dict[str, object]:
    features = dict(existing or {})
    features["helper_tools"] = True
    features["advanced_ai_helpers"] = code in {"growth", "scale"}
    return features


def _updated_limits(code: str, existing: dict[str, object] | None) -> dict[str, object]:
    limits = dict(existing or {})
    if code == "starter":
        limits["max_monthly_helper_runs"] = 80
        limits["max_monthly_advanced_helper_runs"] = 10
        limits["max_saved_helper_artifacts"] = 20
    elif code == "growth":
        limits["max_monthly_helper_runs"] = 400
        limits["max_monthly_advanced_helper_runs"] = 120
        limits["max_saved_helper_artifacts"] = 150
    elif code == "scale":
        limits["max_monthly_helper_runs"] = None
        limits["max_monthly_advanced_helper_runs"] = None
        limits["max_saved_helper_artifacts"] = None
    return limits


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            plans_table.c.code,
            plans_table.c.features,
            plans_table.c.limits,
        )
    ).mappings()

    for row in rows:
        bind.execute(
            plans_table.update()
            .where(plans_table.c.code == row["code"])
            .values(
                features=_updated_features(row["code"], row["features"]),
                limits=_updated_limits(row["code"], row["limits"]),
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            plans_table.c.code,
            plans_table.c.features,
            plans_table.c.limits,
        )
    ).mappings()

    for row in rows:
        features = dict(row["features"] or {})
        limits = dict(row["limits"] or {})
        for key in ("helper_tools", "advanced_ai_helpers"):
            features.pop(key, None)
        for key in (
            "max_monthly_helper_runs",
            "max_monthly_advanced_helper_runs",
            "max_saved_helper_artifacts",
        ):
            limits.pop(key, None)

        bind.execute(
            plans_table.update()
            .where(plans_table.c.code == row["code"])
            .values(features=features, limits=limits)
        )
