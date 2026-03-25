"""phase 7 collaboration foundation

Revision ID: 20260325_0007
Revises: 20260325_0006
Create Date: 2026-03-25 18:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0007"
down_revision = "20260325_0006"
branch_labels = None
depends_on = None


comment_entity_type_enum = sa.Enum(
    "campaign",
    "draft",
    name="comment_entity_type",
    native_enum=False,
)
assignment_entity_type_enum = sa.Enum(
    "campaign",
    "draft",
    "review_task",
    name="assignment_entity_type",
    native_enum=False,
)
assignment_status_enum = sa.Enum(
    "open",
    "completed",
    "canceled",
    name="assignment_status",
    native_enum=False,
)
notification_type_enum = sa.Enum(
    "mention",
    "review_requested",
    "draft_approved",
    "draft_rejected",
    "assignment_created",
    "due_soon",
    name="notification_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "collaboration_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", comment_entity_type_enum, nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("draft_id", sa.Integer(), nullable=True),
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], name=op.f("fk_collaboration_comments_author_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], name=op.f("fk_collaboration_comments_brand_id_brands"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], name=op.f("fk_collaboration_comments_campaign_id_campaigns"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_id"], ["content_drafts.id"], name=op.f("fk_collaboration_comments_draft_id_content_drafts"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["collaboration_comments.id"], name=op.f("fk_collaboration_comments_parent_comment_id_collaboration_comments"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collaboration_comments")),
    )
    op.create_index(op.f("ix_collaboration_comments_author_user_id"), "collaboration_comments", ["author_user_id"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_brand_id"), "collaboration_comments", ["brand_id"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_campaign_id"), "collaboration_comments", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_draft_id"), "collaboration_comments", ["draft_id"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_entity_id"), "collaboration_comments", ["entity_id"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_entity_type"), "collaboration_comments", ["entity_type"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_id"), "collaboration_comments", ["id"], unique=False)
    op.create_index(op.f("ix_collaboration_comments_parent_comment_id"), "collaboration_comments", ["parent_comment_id"], unique=False)

    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("assignment_type", assignment_entity_type_enum, nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("draft_id", sa.Integer(), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("assignee_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", assignment_status_enum, nullable=False, server_default=sa.text("'open'")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], name=op.f("fk_assignments_assignee_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], name=op.f("fk_assignments_assigned_by_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], name=op.f("fk_assignments_brand_id_brands"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], name=op.f("fk_assignments_campaign_id_campaigns"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_id"], ["content_drafts.id"], name=op.f("fk_assignments_draft_id_content_drafts"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    op.create_index(op.f("ix_assignments_assignee_user_id"), "assignments", ["assignee_user_id"], unique=False)
    op.create_index(op.f("ix_assignments_assigned_by_user_id"), "assignments", ["assigned_by_user_id"], unique=False)
    op.create_index(op.f("ix_assignments_assignment_type"), "assignments", ["assignment_type"], unique=False)
    op.create_index(op.f("ix_assignments_brand_id"), "assignments", ["brand_id"], unique=False)
    op.create_index(op.f("ix_assignments_campaign_id"), "assignments", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_assignments_draft_id"), "assignments", ["draft_id"], unique=False)
    op.create_index(op.f("ix_assignments_due_at"), "assignments", ["due_at"], unique=False)
    op.create_index(op.f("ix_assignments_entity_id"), "assignments", ["entity_id"], unique=False)
    op.create_index(op.f("ix_assignments_id"), "assignments", ["id"], unique=False)
    op.create_index(op.f("ix_assignments_status"), "assignments", ["status"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_notifications_actor_user_id_users"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], name=op.f("fk_notifications_brand_id_brands"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_notifications_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
        sa.UniqueConstraint("dedupe_key", name=op.f("uq_notifications_dedupe_key")),
    )
    op.create_index(op.f("ix_notifications_actor_user_id"), "notifications", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_notifications_brand_id"), "notifications", ["brand_id"], unique=False)
    op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"], unique=False)
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_notification_type"), "notifications", ["notification_type"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)

    op.create_table(
        "mentions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=False),
        sa.Column("mentioned_user_id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(length=255), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=True),
        sa.Column("draft_review_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], name=op.f("fk_mentions_author_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], name=op.f("fk_mentions_brand_id_brands"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["collaboration_comments.id"], name=op.f("fk_mentions_comment_id_collaboration_comments"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_review_id"], ["draft_reviews.id"], name=op.f("fk_mentions_draft_review_id_draft_reviews"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentioned_user_id"], ["users.id"], name=op.f("fk_mentions_mentioned_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mentions")),
    )
    op.create_index(op.f("ix_mentions_author_user_id"), "mentions", ["author_user_id"], unique=False)
    op.create_index(op.f("ix_mentions_brand_id"), "mentions", ["brand_id"], unique=False)
    op.create_index(op.f("ix_mentions_comment_id"), "mentions", ["comment_id"], unique=False)
    op.create_index(op.f("ix_mentions_draft_review_id"), "mentions", ["draft_review_id"], unique=False)
    op.create_index(op.f("ix_mentions_id"), "mentions", ["id"], unique=False)
    op.create_index(op.f("ix_mentions_mentioned_user_id"), "mentions", ["mentioned_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mentions_mentioned_user_id"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_id"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_draft_review_id"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_comment_id"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_brand_id"), table_name="mentions")
    op.drop_index(op.f("ix_mentions_author_user_id"), table_name="mentions")
    op.drop_table("mentions")

    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_notification_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_created_at"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_brand_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_actor_user_id"), table_name="notifications")
    op.drop_table("notifications")

    op.drop_index(op.f("ix_assignments_status"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_entity_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_due_at"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_draft_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_campaign_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_brand_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_assignment_type"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_assigned_by_user_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_assignee_user_id"), table_name="assignments")
    op.drop_table("assignments")

    op.drop_index(op.f("ix_collaboration_comments_parent_comment_id"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_id"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_entity_type"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_entity_id"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_draft_id"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_campaign_id"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_brand_id"), table_name="collaboration_comments")
    op.drop_index(op.f("ix_collaboration_comments_author_user_id"), table_name="collaboration_comments")
    op.drop_table("collaboration_comments")
