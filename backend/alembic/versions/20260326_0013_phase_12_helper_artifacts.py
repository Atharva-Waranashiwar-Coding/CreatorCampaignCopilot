"""phase 12 helper artifacts

Revision ID: 20260326_0013
Revises: 20260326_0012
Create Date: 2026-03-26 12:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260326_0013"
down_revision = "20260326_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "draft_helper_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("artifact_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default=sa.text("'saved'")),
        sa.Column("source_tool_usage_log_id", sa.Integer(), nullable=True),
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
            ["draft_id"],
            ["content_drafts.id"],
            name=op.f("fk_draft_helper_artifacts_draft_id_content_drafts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_tool_usage_log_id"],
            ["tool_usage_logs.id"],
            name=op.f("fk_draft_helper_artifacts_source_tool_usage_log_id_tool_usage_logs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_draft_helper_artifacts_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_helper_artifacts")),
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_id"),
        "draft_helper_artifacts",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_draft_id"),
        "draft_helper_artifacts",
        ["draft_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_tool_name"),
        "draft_helper_artifacts",
        ["tool_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_artifact_type"),
        "draft_helper_artifacts",
        ["artifact_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_status"),
        "draft_helper_artifacts",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_source_tool_usage_log_id"),
        "draft_helper_artifacts",
        ["source_tool_usage_log_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_draft_helper_artifacts_created_by"),
        "draft_helper_artifacts",
        ["created_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_draft_helper_artifacts_created_by"), table_name="draft_helper_artifacts")
    op.drop_index(op.f("ix_draft_helper_artifacts_source_tool_usage_log_id"), table_name="draft_helper_artifacts")
    op.drop_index(op.f("ix_draft_helper_artifacts_status"), table_name="draft_helper_artifacts")
    op.drop_index(op.f("ix_draft_helper_artifacts_artifact_type"), table_name="draft_helper_artifacts")
    op.drop_index(op.f("ix_draft_helper_artifacts_tool_name"), table_name="draft_helper_artifacts")
    op.drop_index(op.f("ix_draft_helper_artifacts_draft_id"), table_name="draft_helper_artifacts")
    op.drop_index(op.f("ix_draft_helper_artifacts_id"), table_name="draft_helper_artifacts")
    op.drop_table("draft_helper_artifacts")
