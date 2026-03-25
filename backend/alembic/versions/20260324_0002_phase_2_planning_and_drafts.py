"""phase 2 planning and drafts

Revision ID: 20260324_0002
Revises: 20260324_0001
Create Date: 2026-03-24 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260324_0002"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


draft_status_enum = sa.Enum(
    "idea",
    "draft",
    "in_review",
    "approved",
    "scheduled",
    "published",
    "rejected",
    name="draft_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "content_briefs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("key_message", sa.Text(), nullable=True),
        sa.Column("call_to_action", sa.Text(), nullable=True),
        sa.Column("tone", sa.Text(), nullable=True),
        sa.Column(
            "channels",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column(
            "themes",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
        sa.Column("references", sa.Text(), nullable=True),
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
            name=op.f("fk_content_briefs_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_briefs")),
        sa.UniqueConstraint("campaign_id", name=op.f("uq_content_briefs_campaign_id")),
    )
    op.create_index(op.f("ix_content_briefs_campaign_id"), "content_briefs", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_content_briefs_id"), "content_briefs", ["id"], unique=False)

    op.create_table(
        "content_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=120), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("content_body", sa.Text(), nullable=True),
        sa.Column(
            "status",
            draft_status_enum,
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column("planned_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "current_version_number",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
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
            name=op.f("fk_content_drafts_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_content_drafts_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_drafts")),
    )
    op.create_index(op.f("ix_content_drafts_campaign_id"), "content_drafts", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_content_drafts_id"), "content_drafts", ["id"], unique=False)
    op.create_index(op.f("ix_content_drafts_platform"), "content_drafts", ["platform"], unique=False)
    op.create_index(op.f("ix_content_drafts_status"), "content_drafts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_content_drafts_status"), table_name="content_drafts")
    op.drop_index(op.f("ix_content_drafts_platform"), table_name="content_drafts")
    op.drop_index(op.f("ix_content_drafts_id"), table_name="content_drafts")
    op.drop_index(op.f("ix_content_drafts_campaign_id"), table_name="content_drafts")
    op.drop_table("content_drafts")

    op.drop_index(op.f("ix_content_briefs_id"), table_name="content_briefs")
    op.drop_index(op.f("ix_content_briefs_campaign_id"), table_name="content_briefs")
    op.drop_table("content_briefs")
