"""phase 10 campaign milestones

Revision ID: 20260325_0009
Revises: 20260325_0008
Create Date: 2026-03-25 20:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0009"
down_revision = "20260325_0008"
branch_labels = None
depends_on = None


campaign_milestone_key_enum = sa.Enum(
    "brief_approved",
    "first_drafts_ready",
    "all_reviews_complete",
    "campaign_launch_ready",
    "campaign_completed",
    name="campaign_milestone_key",
    native_enum=False,
)

DEFAULT_CAMPAIGN_MILESTONES = [
    {"key": "brief_approved", "label": "Brief approved", "sort_order": 10},
    {"key": "first_drafts_ready", "label": "First drafts ready", "sort_order": 20},
    {"key": "all_reviews_complete", "label": "All reviews complete", "sort_order": 30},
    {"key": "campaign_launch_ready", "label": "Campaign launch ready", "sort_order": 40},
    {"key": "campaign_completed", "label": "Campaign completed", "sort_order": 50},
]


def upgrade() -> None:
    op.create_table(
        "campaign_milestones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("key", campaign_milestone_key_enum, nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_campaign_milestones_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_user_id"],
            ["users.id"],
            name=op.f("fk_campaign_milestones_completed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_milestones")),
        sa.UniqueConstraint("campaign_id", "key", name="uq_campaign_milestones_campaign_key"),
    )
    op.create_index(op.f("ix_campaign_milestones_campaign_id"), "campaign_milestones", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_milestones_id"), "campaign_milestones", ["id"], unique=False)
    op.create_index(op.f("ix_campaign_milestones_sort_order"), "campaign_milestones", ["sort_order"], unique=False)

    bind = op.get_bind()
    campaign_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM campaigns")).fetchall()]
    if campaign_ids:
        campaign_milestones_table = sa.table(
            "campaign_milestones",
            sa.column("campaign_id", sa.Integer),
            sa.column("key", campaign_milestone_key_enum),
            sa.column("label", sa.String),
            sa.column("sort_order", sa.Integer),
        )
        op.bulk_insert(
            campaign_milestones_table,
            [
                {
                    "campaign_id": campaign_id,
                    "key": milestone["key"],
                    "label": milestone["label"],
                    "sort_order": milestone["sort_order"],
                }
                for campaign_id in campaign_ids
                for milestone in DEFAULT_CAMPAIGN_MILESTONES
            ],
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_milestones_sort_order"), table_name="campaign_milestones")
    op.drop_index(op.f("ix_campaign_milestones_id"), table_name="campaign_milestones")
    op.drop_index(op.f("ix_campaign_milestones_campaign_id"), table_name="campaign_milestones")
    op.drop_table("campaign_milestones")
