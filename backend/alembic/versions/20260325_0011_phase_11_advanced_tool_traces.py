"""phase 11 advanced tool traces

Revision ID: 20260325_0011
Revises: 20260325_0010
Create Date: 2026-03-25 18:15:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0011"
down_revision = "20260325_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tool_usage_logs", sa.Column("campaign_id", sa.Integer(), nullable=True))
    op.add_column("tool_usage_logs", sa.Column("draft_id", sa.Integer(), nullable=True))
    op.add_column("tool_usage_logs", sa.Column("request_trace", sa.JSON(), nullable=True))
    op.add_column("tool_usage_logs", sa.Column("result_trace", sa.JSON(), nullable=True))
    op.create_foreign_key(
        op.f("fk_tool_usage_logs_campaign_id_campaigns"),
        "tool_usage_logs",
        "campaigns",
        ["campaign_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_tool_usage_logs_draft_id_content_drafts"),
        "tool_usage_logs",
        "content_drafts",
        ["draft_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_tool_usage_logs_campaign_id"), "tool_usage_logs", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_tool_usage_logs_draft_id"), "tool_usage_logs", ["draft_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_usage_logs_draft_id"), table_name="tool_usage_logs")
    op.drop_index(op.f("ix_tool_usage_logs_campaign_id"), table_name="tool_usage_logs")
    op.drop_constraint(op.f("fk_tool_usage_logs_draft_id_content_drafts"), "tool_usage_logs", type_="foreignkey")
    op.drop_constraint(op.f("fk_tool_usage_logs_campaign_id_campaigns"), "tool_usage_logs", type_="foreignkey")
    op.drop_column("tool_usage_logs", "result_trace")
    op.drop_column("tool_usage_logs", "request_trace")
    op.drop_column("tool_usage_logs", "draft_id")
    op.drop_column("tool_usage_logs", "campaign_id")
