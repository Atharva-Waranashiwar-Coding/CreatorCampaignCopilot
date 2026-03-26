"""phase 12 helper usage controls

Revision ID: 20260326_0014
Revises: 20260326_0013
Create Date: 2026-03-26 16:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260326_0014"
down_revision = "20260326_0013"
branch_labels = None
depends_on = None


plans_table = sa.table(
    "plans",
    sa.column("code", sa.String()),
    sa.column("limits", sa.JSON()),
)


def _updated_limits(code: str, existing: dict[str, object] | None) -> dict[str, object]:
    limits = dict(existing or {})
    if code == "starter":
        limits["max_helper_runs_per_10_minutes"] = 12
        limits["max_advanced_helper_runs_per_10_minutes"] = 4
    elif code == "growth":
        limits["max_helper_runs_per_10_minutes"] = 40
        limits["max_advanced_helper_runs_per_10_minutes"] = 12
    elif code == "scale":
        limits["max_helper_runs_per_10_minutes"] = 120
        limits["max_advanced_helper_runs_per_10_minutes"] = 40
    return limits


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(plans_table.c.code, plans_table.c.limits)).mappings()

    for row in rows:
        bind.execute(
            plans_table.update()
            .where(plans_table.c.code == row["code"])
            .values(limits=_updated_limits(row["code"], row["limits"]))
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(plans_table.c.code, plans_table.c.limits)).mappings()

    for row in rows:
        limits = dict(row["limits"] or {})
        limits.pop("max_helper_runs_per_10_minutes", None)
        limits.pop("max_advanced_helper_runs_per_10_minutes", None)

        bind.execute(
            plans_table.update()
            .where(plans_table.c.code == row["code"])
            .values(limits=limits)
        )
