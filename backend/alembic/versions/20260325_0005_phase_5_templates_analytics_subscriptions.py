"""phase 5 templates analytics subscriptions

Revision ID: 20260325_0005
Revises: 20260325_0004
Create Date: 2026-03-25 13:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0005"
down_revision = "20260325_0004"
branch_labels = None
depends_on = None


plan_interval_enum = sa.Enum(
    "monthly",
    "yearly",
    name="plan_interval",
    native_enum=False,
)
subscription_status_enum = sa.Enum(
    "trialing",
    "active",
    "past_due",
    "canceled",
    name="subscription_status",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False),
        sa.Column("yearly_price_cents", sa.Integer(), nullable=True),
        sa.Column("limits", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plans")),
        sa.UniqueConstraint("code", name=op.f("uq_plans_code")),
    )
    op.create_index(op.f("ix_plans_code"), "plans", ["code"], unique=True)
    op.create_index(op.f("ix_plans_id"), "plans", ["id"], unique=False)

    op.bulk_insert(
        sa.table(
            "plans",
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("description", sa.Text()),
            sa.column("monthly_price_cents", sa.Integer()),
            sa.column("yearly_price_cents", sa.Integer()),
            sa.column("limits", sa.JSON()),
            sa.column("features", sa.JSON()),
            sa.column("is_active", sa.Boolean()),
            sa.column("sort_order", sa.Integer()),
        ),
        [
            {
                "code": "starter",
                "name": "Starter",
                "description": "Baseline plan for small brand workspaces.",
                "monthly_price_cents": 0,
                "yearly_price_cents": 0,
                "limits": {
                    "max_members": 5,
                    "max_active_campaigns": 4,
                    "max_templates": 5,
                    "max_scheduled_items": 20,
                    "max_monthly_review_actions": 60,
                },
                "features": {
                    "template_library": True,
                    "advanced_analytics": False,
                    "priority_support": False,
                },
                "is_active": True,
                "sort_order": 1,
            },
            {
                "code": "growth",
                "name": "Growth",
                "description": "Higher limits and advanced dashboard analytics.",
                "monthly_price_cents": 9900,
                "yearly_price_cents": 99000,
                "limits": {
                    "max_members": 15,
                    "max_active_campaigns": 12,
                    "max_templates": 25,
                    "max_scheduled_items": 120,
                    "max_monthly_review_actions": 300,
                },
                "features": {
                    "template_library": True,
                    "advanced_analytics": True,
                    "priority_support": False,
                },
                "is_active": True,
                "sort_order": 2,
            },
            {
                "code": "scale",
                "name": "Scale",
                "description": "Expanded operating limits for larger campaign teams.",
                "monthly_price_cents": 24900,
                "yearly_price_cents": 249000,
                "limits": {
                    "max_members": None,
                    "max_active_campaigns": None,
                    "max_templates": None,
                    "max_scheduled_items": None,
                    "max_monthly_review_actions": None,
                },
                "features": {
                    "template_library": True,
                    "advanced_analytics": True,
                    "priority_support": True,
                },
                "is_active": True,
                "sort_order": 3,
            },
        ],
    )

    op.create_table(
        "brand_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", subscription_status_enum, nullable=False, server_default=sa.text("'active'")),
        sa.Column("billing_interval", plan_interval_enum, nullable=False, server_default=sa.text("'monthly'")),
        sa.Column("external_subscription_id", sa.String(length=120), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("plan_snapshot", sa.JSON(), nullable=False),
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
            name=op.f("fk_brand_subscriptions_brand_id_brands"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["plans.id"],
            name=op.f("fk_brand_subscriptions_plan_id_plans"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_brand_subscriptions")),
        sa.UniqueConstraint("brand_id", name=op.f("uq_brand_subscriptions_brand_id")),
    )
    op.create_index(op.f("ix_brand_subscriptions_brand_id"), "brand_subscriptions", ["brand_id"], unique=True)
    op.create_index(op.f("ix_brand_subscriptions_id"), "brand_subscriptions", ["id"], unique=False)
    op.create_index(op.f("ix_brand_subscriptions_plan_id"), "brand_subscriptions", ["plan_id"], unique=False)
    op.create_index(op.f("ix_brand_subscriptions_status"), "brand_subscriptions", ["status"], unique=False)

    op.execute(
        """
        INSERT INTO brand_subscriptions (
            brand_id,
            plan_id,
            status,
            billing_interval,
            current_period_start,
            current_period_end,
            cancel_at_period_end,
            plan_snapshot
        )
        SELECT
            brands.id,
            plans.id,
            'active',
            'monthly',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP + INTERVAL '30 days',
            false,
            json_build_object(
                'code', plans.code,
                'name', plans.name,
                'monthly_price_cents', plans.monthly_price_cents,
                'yearly_price_cents', plans.yearly_price_cents,
                'limits', plans.limits,
                'features', plans.features
            )
        FROM brands
        CROSS JOIN plans
        WHERE plans.code = 'starter'
        """
    )

    op.create_table(
        "content_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_type", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=120), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
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
            name=op.f("fk_content_templates_brand_id_brands"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_content_templates_created_by_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_templates")),
    )
    op.create_index(op.f("ix_content_templates_brand_id"), "content_templates", ["brand_id"], unique=False)
    op.create_index(op.f("ix_content_templates_id"), "content_templates", ["id"], unique=False)
    op.create_index(op.f("ix_content_templates_platform"), "content_templates", ["platform"], unique=False)
    op.create_index(op.f("ix_content_templates_template_type"), "content_templates", ["template_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_content_templates_template_type"), table_name="content_templates")
    op.drop_index(op.f("ix_content_templates_platform"), table_name="content_templates")
    op.drop_index(op.f("ix_content_templates_id"), table_name="content_templates")
    op.drop_index(op.f("ix_content_templates_brand_id"), table_name="content_templates")
    op.drop_table("content_templates")

    op.drop_index(op.f("ix_brand_subscriptions_status"), table_name="brand_subscriptions")
    op.drop_index(op.f("ix_brand_subscriptions_plan_id"), table_name="brand_subscriptions")
    op.drop_index(op.f("ix_brand_subscriptions_id"), table_name="brand_subscriptions")
    op.drop_index(op.f("ix_brand_subscriptions_brand_id"), table_name="brand_subscriptions")
    op.drop_table("brand_subscriptions")

    op.drop_index(op.f("ix_plans_id"), table_name="plans")
    op.drop_index(op.f("ix_plans_code"), table_name="plans")
    op.drop_table("plans")
