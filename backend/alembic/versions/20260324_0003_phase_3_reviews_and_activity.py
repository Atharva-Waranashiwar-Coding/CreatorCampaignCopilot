"""phase 3 reviews and activity

Revision ID: 20260324_0003
Revises: 20260324_0002
Create Date: 2026-03-24 09:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260324_0003"
down_revision = "20260324_0002"
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

draft_review_action_enum = sa.Enum(
    "commented",
    "submitted",
    "approved",
    "rejected",
    "resubmitted",
    name="draft_review_action",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "draft_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", draft_review_action_enum, nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("version_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("from_status", draft_status_enum, nullable=True),
        sa.Column("to_status", draft_status_enum, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_draft_reviews_actor_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["content_drafts.id"],
            name=op.f("fk_draft_reviews_draft_id_content_drafts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_reviews")),
    )
    op.create_index(op.f("ix_draft_reviews_action"), "draft_reviews", ["action"], unique=False)
    op.create_index(op.f("ix_draft_reviews_actor_user_id"), "draft_reviews", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_draft_reviews_created_at"), "draft_reviews", ["created_at"], unique=False)
    op.create_index(op.f("ix_draft_reviews_draft_id"), "draft_reviews", ["draft_id"], unique=False)
    op.create_index(op.f("ix_draft_reviews_id"), "draft_reviews", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_draft_reviews_id"), table_name="draft_reviews")
    op.drop_index(op.f("ix_draft_reviews_draft_id"), table_name="draft_reviews")
    op.drop_index(op.f("ix_draft_reviews_created_at"), table_name="draft_reviews")
    op.drop_index(op.f("ix_draft_reviews_actor_user_id"), table_name="draft_reviews")
    op.drop_index(op.f("ix_draft_reviews_action"), table_name="draft_reviews")
    op.drop_table("draft_reviews")
