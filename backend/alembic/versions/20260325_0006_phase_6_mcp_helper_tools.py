"""phase 6 mcp helper tools

Revision ID: 20260325_0006
Revises: 20260325_0005
Create Date: 2026-03-25 15:35:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0006"
down_revision = "20260325_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_usage_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("target_entity_type", sa.String(length=80), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=True),
        sa.Column("invocation_source", sa.String(length=40), nullable=False, server_default=sa.text("'rest'")),
        sa.Column("was_successful", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_tool_usage_logs_actor_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["brand_id"],
            ["brands.id"],
            name=op.f("fk_tool_usage_logs_brand_id_brands"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_usage_logs")),
    )
    op.create_index(op.f("ix_tool_usage_logs_actor_user_id"), "tool_usage_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_tool_usage_logs_brand_id"), "tool_usage_logs", ["brand_id"], unique=False)
    op.create_index(op.f("ix_tool_usage_logs_id"), "tool_usage_logs", ["id"], unique=False)
    op.create_index(op.f("ix_tool_usage_logs_tool_name"), "tool_usage_logs", ["tool_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_usage_logs_tool_name"), table_name="tool_usage_logs")
    op.drop_index(op.f("ix_tool_usage_logs_id"), table_name="tool_usage_logs")
    op.drop_index(op.f("ix_tool_usage_logs_brand_id"), table_name="tool_usage_logs")
    op.drop_index(op.f("ix_tool_usage_logs_actor_user_id"), table_name="tool_usage_logs")
    op.drop_table("tool_usage_logs")
