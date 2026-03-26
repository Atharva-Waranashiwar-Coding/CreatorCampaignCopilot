"""phase 10 campaign dependencies

Revision ID: 20260325_0010
Revises: 20260325_0009
Create Date: 2026-03-25 21:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0010"
down_revision = "20260325_0009"
branch_labels = None
depends_on = None


campaign_dependency_node_type_enum = sa.Enum(
    "campaign_milestone",
    "draft_stage",
    name="campaign_dependency_node_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "campaign_dependencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("dependent_type", campaign_dependency_node_type_enum, nullable=False),
        sa.Column("dependent_milestone_id", sa.Integer(), nullable=True),
        sa.Column("dependent_draft_id", sa.Integer(), nullable=True),
        sa.Column("dependent_stage_key", sa.String(length=120), nullable=True),
        sa.Column("blocker_type", campaign_dependency_node_type_enum, nullable=False),
        sa.Column("blocker_milestone_id", sa.Integer(), nullable=True),
        sa.Column("blocker_draft_id", sa.Integer(), nullable=True),
        sa.Column("blocker_stage_key", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
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
            name=op.f("fk_campaign_dependencies_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dependent_milestone_id"],
            ["campaign_milestones.id"],
            name=op.f("fk_campaign_dependencies_dependent_milestone_id_campaign_milestones"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dependent_draft_id"],
            ["content_drafts.id"],
            name=op.f("fk_campaign_dependencies_dependent_draft_id_content_drafts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocker_milestone_id"],
            ["campaign_milestones.id"],
            name=op.f("fk_campaign_dependencies_blocker_milestone_id_campaign_milestones"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocker_draft_id"],
            ["content_drafts.id"],
            name=op.f("fk_campaign_dependencies_blocker_draft_id_content_drafts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_campaign_dependencies_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_dependencies")),
    )
    op.create_index(op.f("ix_campaign_dependencies_campaign_id"), "campaign_dependencies", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_dependencies_id"), "campaign_dependencies", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_dependencies_id"), table_name="campaign_dependencies")
    op.drop_index(op.f("ix_campaign_dependencies_campaign_id"), table_name="campaign_dependencies")
    op.drop_table("campaign_dependencies")
