"""phase 4 assets versions calendar

Revision ID: 20260325_0004
Revises: 20260324_0003
Create Date: 2026-03-25 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0004"
down_revision = "20260324_0003"
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
        "campaign_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=80), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            name=op.f("fk_campaign_assets_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_campaign_assets_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_assets")),
    )
    op.create_index(op.f("ix_campaign_assets_asset_type"), "campaign_assets", ["asset_type"], unique=False)
    op.create_index(op.f("ix_campaign_assets_campaign_id"), "campaign_assets", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_assets_id"), "campaign_assets", ["id"], unique=False)

    op.create_table(
        "draft_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=120), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("content_body", sa.Text(), nullable=True),
        sa.Column("status", draft_status_enum, nullable=False),
        sa.Column("planned_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_draft_versions_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["content_drafts.id"],
            name=op.f("fk_draft_versions_draft_id_content_drafts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_draft_versions")),
        sa.UniqueConstraint("draft_id", "version_number", name="uq_draft_versions_draft_version_number"),
    )
    op.create_index(op.f("ix_draft_versions_draft_id"), "draft_versions", ["draft_id"], unique=False)
    op.create_index(op.f("ix_draft_versions_id"), "draft_versions", ["id"], unique=False)
    op.create_index(op.f("ix_draft_versions_version_number"), "draft_versions", ["version_number"], unique=False)

    op.create_table(
        "calendar_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.Integer(), nullable=False),
        sa.Column("draft_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=120), nullable=True),
        sa.Column("item_type", sa.String(length=80), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            ["brand_id"],
            ["brands.id"],
            name=op.f("fk_calendar_items_brand_id_brands"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name=op.f("fk_calendar_items_campaign_id_campaigns"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_calendar_items_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["content_drafts.id"],
            name=op.f("fk_calendar_items_draft_id_content_drafts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_items")),
        sa.UniqueConstraint("draft_id", name=op.f("uq_calendar_items_draft_id")),
    )
    op.create_index(op.f("ix_calendar_items_brand_id"), "calendar_items", ["brand_id"], unique=False)
    op.create_index(op.f("ix_calendar_items_campaign_id"), "calendar_items", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_calendar_items_id"), "calendar_items", ["id"], unique=False)
    op.create_index(op.f("ix_calendar_items_item_type"), "calendar_items", ["item_type"], unique=False)
    op.create_index(op.f("ix_calendar_items_scheduled_for"), "calendar_items", ["scheduled_for"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_items_scheduled_for"), table_name="calendar_items")
    op.drop_index(op.f("ix_calendar_items_item_type"), table_name="calendar_items")
    op.drop_index(op.f("ix_calendar_items_id"), table_name="calendar_items")
    op.drop_index(op.f("ix_calendar_items_campaign_id"), table_name="calendar_items")
    op.drop_index(op.f("ix_calendar_items_brand_id"), table_name="calendar_items")
    op.drop_table("calendar_items")

    op.drop_index(op.f("ix_draft_versions_version_number"), table_name="draft_versions")
    op.drop_index(op.f("ix_draft_versions_id"), table_name="draft_versions")
    op.drop_index(op.f("ix_draft_versions_draft_id"), table_name="draft_versions")
    op.drop_table("draft_versions")

    op.drop_index(op.f("ix_campaign_assets_id"), table_name="campaign_assets")
    op.drop_index(op.f("ix_campaign_assets_campaign_id"), table_name="campaign_assets")
    op.drop_index(op.f("ix_campaign_assets_asset_type"), table_name="campaign_assets")
    op.drop_table("campaign_assets")
