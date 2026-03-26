"""phase 10 workflow foundation

Revision ID: 20260325_0008
Revises: 20260325_0007
Create Date: 2026-03-25 20:15:00
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0008"
down_revision = "20260325_0007"
branch_labels = None
depends_on = None


DEFAULT_DRAFT_WORKFLOW_CONFIG = [
    {
        "key": "idea",
        "label": "Idea",
        "stage_type": "backlog",
        "color": "amber",
        "description": "Loose concepts and early hooks.",
        "is_initial": True,
        "allowed_next_stage_keys": ["draft", "in_review"],
    },
    {
        "key": "draft",
        "label": "Draft",
        "stage_type": "in_progress",
        "color": "sky",
        "description": "Working copy in active editing.",
        "is_initial": True,
        "allowed_next_stage_keys": ["idea", "in_review"],
    },
    {
        "key": "in_review",
        "label": "In Review",
        "stage_type": "review",
        "color": "amber",
        "description": "Waiting on review feedback.",
        "is_initial": True,
        "allowed_next_stage_keys": ["approved", "rejected"],
    },
    {
        "key": "approved",
        "label": "Approved",
        "stage_type": "approved",
        "color": "emerald",
        "description": "Cleared and ready to schedule.",
        "is_initial": False,
        "allowed_next_stage_keys": ["scheduled", "published"],
    },
    {
        "key": "scheduled",
        "label": "Scheduled",
        "stage_type": "scheduled",
        "color": "cyan",
        "description": "Placed on the campaign calendar.",
        "is_initial": False,
        "allowed_next_stage_keys": ["published"],
    },
    {
        "key": "published",
        "label": "Published",
        "stage_type": "published",
        "color": "slate",
        "description": "Live and shipped.",
        "is_initial": False,
        "allowed_next_stage_keys": [],
    },
    {
        "key": "rejected",
        "label": "Needs Changes",
        "stage_type": "changes_requested",
        "color": "rose",
        "description": "Needs changes before the next review pass.",
        "is_initial": False,
        "allowed_next_stage_keys": ["in_review"],
    },
]

DEFAULT_STATUS_KEYS = (
    "idea",
    "draft",
    "in_review",
    "approved",
    "scheduled",
    "published",
    "rejected",
)


def upgrade() -> None:
    default_workflow_json = json.dumps(DEFAULT_DRAFT_WORKFLOW_CONFIG).replace("'", "''")

    op.add_column("brands", sa.Column("draft_workflow_config", sa.JSON(), nullable=True))
    op.execute(
        f"""
        UPDATE brands
        SET draft_workflow_config = '{default_workflow_json}'::json
        WHERE draft_workflow_config IS NULL
        """
    )
    op.alter_column("brands", "draft_workflow_config", nullable=False)

    op.add_column(
        "content_drafts",
        sa.Column("status_key", sa.String(length=120), server_default=sa.text("'draft'"), nullable=False),
    )
    op.execute("UPDATE content_drafts SET status_key = status")
    op.drop_index(op.f("ix_content_drafts_status"), table_name="content_drafts")
    op.drop_column("content_drafts", "status")
    op.alter_column("content_drafts", "status_key", new_column_name="status")
    op.create_index(op.f("ix_content_drafts_status"), "content_drafts", ["status"], unique=False)

    op.add_column(
        "draft_versions",
        sa.Column("status_key", sa.String(length=120), server_default=sa.text("'draft'"), nullable=False),
    )
    op.execute("UPDATE draft_versions SET status_key = status")
    op.drop_column("draft_versions", "status")
    op.alter_column("draft_versions", "status_key", new_column_name="status")

    op.add_column("draft_reviews", sa.Column("from_status_key", sa.String(length=120), nullable=True))
    op.add_column("draft_reviews", sa.Column("to_status_key", sa.String(length=120), nullable=True))
    op.execute("UPDATE draft_reviews SET from_status_key = from_status, to_status_key = to_status")
    op.drop_column("draft_reviews", "from_status")
    op.drop_column("draft_reviews", "to_status")
    op.alter_column("draft_reviews", "from_status_key", new_column_name="from_status")
    op.alter_column("draft_reviews", "to_status_key", new_column_name="to_status")


def downgrade() -> None:
    draft_status_enum = sa.Enum(*DEFAULT_STATUS_KEYS, name="draft_status", native_enum=False)

    valid_status_list = ", ".join(f"'{status}'" for status in DEFAULT_STATUS_KEYS)
    draft_status_case = (
        f"CASE WHEN status IN ({valid_status_list}) THEN status ELSE 'draft' END"
    )
    review_status_case = (
        f"CASE WHEN {{column_name}} IN ({valid_status_list}) THEN {{column_name}} ELSE NULL END"
    )

    op.add_column(
        "content_drafts",
        sa.Column("status_enum", draft_status_enum, server_default=sa.text("'draft'"), nullable=False),
    )
    op.execute(f"UPDATE content_drafts SET status_enum = {draft_status_case}")
    op.drop_index(op.f("ix_content_drafts_status"), table_name="content_drafts")
    op.drop_column("content_drafts", "status")
    op.alter_column("content_drafts", "status_enum", new_column_name="status")
    op.create_index(op.f("ix_content_drafts_status"), "content_drafts", ["status"], unique=False)

    op.add_column(
        "draft_versions",
        sa.Column("status_enum", draft_status_enum, server_default=sa.text("'draft'"), nullable=False),
    )
    op.execute(f"UPDATE draft_versions SET status_enum = {draft_status_case}")
    op.drop_column("draft_versions", "status")
    op.alter_column("draft_versions", "status_enum", new_column_name="status")

    op.add_column("draft_reviews", sa.Column("from_status_enum", draft_status_enum, nullable=True))
    op.add_column("draft_reviews", sa.Column("to_status_enum", draft_status_enum, nullable=True))
    op.execute(
        f"""
        UPDATE draft_reviews
        SET from_status_enum = {review_status_case.format(column_name='from_status')},
            to_status_enum = {review_status_case.format(column_name='to_status')}
        """
    )
    op.drop_column("draft_reviews", "from_status")
    op.drop_column("draft_reviews", "to_status")
    op.alter_column("draft_reviews", "from_status_enum", new_column_name="from_status")
    op.alter_column("draft_reviews", "to_status_enum", new_column_name="to_status")

    op.drop_column("brands", "draft_workflow_config")
