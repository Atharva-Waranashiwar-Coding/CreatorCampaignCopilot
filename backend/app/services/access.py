from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import CampaignStatus, MembershipStatus, PlanInterval, SubscriptionStatus
from app.core.permissions import BRAND_MANAGEMENT_ROLES, require_role
from app.models.audit_log import AuditLog
from app.models.brand import Brand
from app.models.brand_membership import BrandMembership
from app.models.brand_subscription import BrandSubscription
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.content_template import ContentTemplate
from app.models.draft_helper_artifact import DraftHelperArtifact
from app.models.draft_review import DraftReview
from app.models.plan import Plan
from app.models.project import Project
from app.models.tool_usage_log import ToolUsageLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.billing import (
    BrandBillingSnapshotRead,
    BrandSubscriptionRead,
    BrandSubscriptionUpdate,
    FeatureAccessRead,
    PlanRead,
    UsageMetricRead,
)
from app.services.audit import record_audit_log
from app.tools.definitions import ADVANCED_HELPER_TOOL_NAMES, get_helper_tool_definition

DEFAULT_PLAN_CODE = "starter"
USAGE_METRIC_DEFINITIONS = {
    "members": {"label": "Members", "limit_key": "max_members"},
    "active_campaigns": {"label": "Active campaigns", "limit_key": "max_active_campaigns"},
    "templates": {"label": "Templates", "limit_key": "max_templates"},
    "scheduled_items": {"label": "Scheduled items", "limit_key": "max_scheduled_items"},
    "monthly_review_actions": {"label": "Monthly reviews", "limit_key": "max_monthly_review_actions"},
    "monthly_helper_runs": {"label": "Monthly helper runs", "limit_key": "max_monthly_helper_runs"},
    "monthly_advanced_helper_runs": {
        "label": "Monthly AI helper runs",
        "limit_key": "max_monthly_advanced_helper_runs",
    },
    "saved_helper_artifacts": {
        "label": "Saved helper artifacts",
        "limit_key": "max_saved_helper_artifacts",
    },
}
FEATURE_DEFINITIONS = {
    "template_library": {
        "label": "Template library",
        "description": "Create and reuse structured content templates at the brand level.",
    },
    "advanced_analytics": {
        "label": "Advanced analytics",
        "description": "Unlock deeper campaign, review, and scheduling visibility.",
    },
    "priority_support": {
        "label": "Priority support",
        "description": "Reserved operating support for larger delivery teams.",
    },
    "helper_tools": {
        "label": "Helper tools",
        "description": "Run deterministic helper utilities against brand, campaign, and draft context.",
    },
    "advanced_ai_helpers": {
        "label": "Advanced AI helpers",
        "description": "Use LLM-backed voice validation, adaptation, and revision-assist workflows.",
    },
}


@dataclass(slots=True)
class BrandAccessContext:
    brand: Brand
    membership: BrandMembership
    subscription: BrandSubscription
    plan: Plan


def _serialize_audit_log(log: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=log.id,
        brand_id=log.brand_id,
        actor_user_id=log.actor_user_id,
        actor_name=log.actor.full_name if log.actor else None,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        action=log.action,
        metadata=log.metadata_json,
        created_at=log.created_at,
    )


def _coerce_limit(value: object | None) -> int | None:
    if value is None:
        return None
    return int(value)


def _serialize_plan(plan: Plan) -> PlanRead:
    features = {key: bool(value) for key, value in (plan.features_json or {}).items()}
    limits = {key: _coerce_limit(value) for key, value in (plan.limits_json or {}).items()}
    return PlanRead(
        id=plan.id,
        code=plan.code,
        name=plan.name,
        description=plan.description,
        monthly_price_cents=plan.monthly_price_cents,
        yearly_price_cents=plan.yearly_price_cents,
        limits=limits,
        features=features,
        is_active=plan.is_active,
        sort_order=plan.sort_order,
    )


def _plan_snapshot(plan: Plan) -> dict[str, object]:
    plan_read = _serialize_plan(plan)
    return plan_read.model_dump()


def _serialize_subscription(subscription: BrandSubscription, *, plan: Plan | None = None) -> BrandSubscriptionRead:
    current_plan = plan or subscription.plan
    snapshot = subscription.plan_snapshot_json or {}
    plan_code = current_plan.code if current_plan else str(snapshot.get("code", ""))
    plan_name = current_plan.name if current_plan else str(snapshot.get("name", ""))

    return BrandSubscriptionRead(
        id=subscription.id,
        brand_id=subscription.brand_id,
        plan_id=subscription.plan_id,
        plan_code=plan_code,
        plan_name=plan_name,
        status=subscription.status,
        billing_interval=subscription.billing_interval,
        external_subscription_id=subscription.external_subscription_id,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


def _get_plan_by_code(db: Session, *, code: str) -> Plan:
    plan = db.scalar(
        select(Plan).where(
            Plan.code == code,
            Plan.is_active.is_(True),
        )
    )
    if plan is None:
        raise LookupError(f"Plan '{code}' was not found.")
    return plan


def _period_end_for_interval(interval: PlanInterval, *, start: datetime) -> datetime:
    days = 365 if interval == PlanInterval.YEARLY else 30
    return start + timedelta(days=days)


def create_default_brand_subscription(
    db: Session,
    *,
    brand: Brand,
    actor_user_id: int | None = None,
) -> BrandSubscription:
    if brand.subscription is not None:
        return brand.subscription

    plan = _get_plan_by_code(db, code=DEFAULT_PLAN_CODE)
    now = datetime.now(UTC)
    subscription = BrandSubscription(
        brand_id=brand.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_interval=PlanInterval.MONTHLY,
        current_period_start=now,
        current_period_end=_period_end_for_interval(PlanInterval.MONTHLY, start=now),
        cancel_at_period_end=False,
        plan_snapshot_json=_plan_snapshot(plan),
    )
    db.add(subscription)
    db.flush()
    brand.subscription = subscription

    if actor_user_id is not None:
        record_audit_log(
            db,
            brand_id=brand.id,
            actor_user_id=actor_user_id,
            entity_type="brand_subscription",
            entity_id=subscription.id,
            action="subscription.created",
            metadata={
                "plan_code": plan.code,
                "plan_name": plan.name,
                "billing_interval": PlanInterval.MONTHLY.value,
            },
        )

    return subscription


def get_brand_access_context(db: Session, *, brand_id: int, user_id: int) -> BrandAccessContext:
    membership = db.scalar(
        select(BrandMembership)
        .options(
            joinedload(BrandMembership.brand)
            .joinedload(Brand.subscription)
            .joinedload(BrandSubscription.plan)
        )
        .where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise PermissionError("You do not have access to this brand.")

    brand = membership.brand
    subscription = brand.subscription or create_default_brand_subscription(db, brand=brand)
    plan = subscription.plan or db.get(Plan, subscription.plan_id)
    if plan is None:
        raise LookupError("The active plan for this brand could not be resolved.")

    return BrandAccessContext(
        brand=brand,
        membership=membership,
        subscription=subscription,
        plan=plan,
    )


def compute_brand_usage_counts(db: Session, *, brand_id: int) -> dict[str, int]:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    members = db.scalar(
        select(func.count(BrandMembership.id)).where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ) or 0
    active_campaigns = db.scalar(
        select(func.count(Campaign.id))
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id == brand_id,
            Campaign.status == CampaignStatus.ACTIVE,
        )
    ) or 0
    templates = db.scalar(
        select(func.count(ContentTemplate.id)).where(ContentTemplate.brand_id == brand_id)
    ) or 0
    scheduled_items = db.scalar(
        select(func.count(CalendarItem.id)).where(
            CalendarItem.brand_id == brand_id,
            CalendarItem.scheduled_for >= now,
        )
    ) or 0
    monthly_review_actions = db.scalar(
        select(func.count(DraftReview.id))
        .join(ContentDraft, ContentDraft.id == DraftReview.draft_id)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id == brand_id,
            DraftReview.created_at >= month_start,
        )
    ) or 0
    monthly_helper_runs = db.scalar(
        select(func.count(ToolUsageLog.id)).where(
            ToolUsageLog.brand_id == brand_id,
            ToolUsageLog.created_at >= month_start,
            ToolUsageLog.was_successful.is_(True),
        )
    ) or 0
    monthly_advanced_helper_runs = db.scalar(
        select(func.count(ToolUsageLog.id)).where(
            ToolUsageLog.brand_id == brand_id,
            ToolUsageLog.created_at >= month_start,
            ToolUsageLog.was_successful.is_(True),
            ToolUsageLog.tool_name.in_(ADVANCED_HELPER_TOOL_NAMES),
        )
    ) or 0
    saved_helper_artifacts = db.scalar(
        select(func.count(DraftHelperArtifact.id))
        .join(ContentDraft, ContentDraft.id == DraftHelperArtifact.draft_id)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id == brand_id)
    ) or 0

    return {
        "members": members,
        "active_campaigns": active_campaigns,
        "templates": templates,
        "scheduled_items": scheduled_items,
        "monthly_review_actions": monthly_review_actions,
        "monthly_helper_runs": monthly_helper_runs,
        "monthly_advanced_helper_runs": monthly_advanced_helper_runs,
        "saved_helper_artifacts": saved_helper_artifacts,
    }


def build_usage_metrics(*, plan: Plan, usage_counts: dict[str, int]) -> list[UsageMetricRead]:
    metrics: list[UsageMetricRead] = []

    for metric_key, definition in USAGE_METRIC_DEFINITIONS.items():
        current = usage_counts.get(metric_key, 0)
        limit = _coerce_limit((plan.limits_json or {}).get(definition["limit_key"]))
        if limit is None:
            metrics.append(
                UsageMetricRead(
                    key=metric_key,
                    label=definition["label"],
                    current=current,
                    limit=None,
                    remaining=None,
                    percent_used=None,
                    status="unlimited",
                )
            )
            continue

        remaining = max(limit - current, 0)
        percent_used = 100 if limit == 0 else min(int((current / limit) * 100), 100)
        status = "ok"
        if current >= limit:
            status = "at_limit"
        elif current >= max(1, int(limit * 0.8)):
            status = "warning"

        metrics.append(
            UsageMetricRead(
                key=metric_key,
                label=definition["label"],
                current=current,
                limit=limit,
                remaining=remaining,
                percent_used=percent_used,
                status=status,
            )
        )

    return metrics


def build_feature_access(*, plan: Plan) -> list[FeatureAccessRead]:
    features = plan.features_json or {}
    return [
        FeatureAccessRead(
            key=feature_key,
            label=definition["label"],
            description=definition["description"],
            enabled=bool(features.get(feature_key, False)),
        )
        for feature_key, definition in FEATURE_DEFINITIONS.items()
    ]


def is_feature_enabled(*, plan: Plan, feature_key: str) -> bool:
    return bool((plan.features_json or {}).get(feature_key, False))


def assert_brand_feature_access(
    db: Session,
    *,
    brand_id: int,
    user_id: int,
    feature_key: str,
    message: str,
) -> BrandAccessContext:
    context = get_brand_access_context(db, brand_id=brand_id, user_id=user_id)
    if not is_feature_enabled(plan=context.plan, feature_key=feature_key):
        raise PermissionError(message)
    return context


def assert_brand_limit_available(
    db: Session,
    *,
    brand_id: int,
    user_id: int,
    metric_key: str,
    increment: int = 1,
    message: str | None = None,
) -> BrandAccessContext:
    context = get_brand_access_context(db, brand_id=brand_id, user_id=user_id)
    definition = USAGE_METRIC_DEFINITIONS.get(metric_key)
    if definition is None:
        raise LookupError(f"Usage metric '{metric_key}' is not configured.")

    limit = _coerce_limit((context.plan.limits_json or {}).get(definition["limit_key"]))
    if limit is None:
        return context

    current_usage = compute_brand_usage_counts(db, brand_id=brand_id).get(metric_key, 0)
    if current_usage + increment > limit:
        raise ValueError(
            message
            or f"{definition['label']} reached the limit for the {context.plan.name} plan. Upgrade to continue."
        )
    return context


def assert_helper_tool_plan_access(
    db: Session,
    *,
    brand_id: int,
    user_id: int,
    tool_name: str,
) -> BrandAccessContext:
    definition = get_helper_tool_definition(tool_name)
    context = assert_brand_feature_access(
        db,
        brand_id=brand_id,
        user_id=user_id,
        feature_key="helper_tools",
        message="Helper tools are not available on this brand plan.",
    )
    if definition.is_advanced:
        assert_brand_feature_access(
            db,
            brand_id=brand_id,
            user_id=user_id,
            feature_key=definition.required_feature_key,
            message="Advanced AI helper tools are not available on this brand plan.",
        )

    assert_brand_limit_available(
        db,
        brand_id=brand_id,
        user_id=user_id,
        metric_key="monthly_helper_runs",
        message="This brand has reached its monthly helper-tool allowance.",
    )
    if definition.is_advanced:
        assert_brand_limit_available(
            db,
            brand_id=brand_id,
            user_id=user_id,
            metric_key=definition.usage_metric_key,
            message="This brand has reached its monthly advanced AI helper allowance.",
        )
    return context


def _list_recent_plan_activity(db: Session, *, brand_id: int) -> list[AuditLogRead]:
    logs = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(
            AuditLog.brand_id == brand_id,
            or_(
                AuditLog.entity_type == "brand_subscription",
                AuditLog.action.like("subscription.%"),
            ),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(8)
    ).all()
    return [_serialize_audit_log(log) for log in logs]


def _build_upgrade_prompts(
    *,
    plan: Plan,
    usage: list[UsageMetricRead],
    features: list[FeatureAccessRead],
) -> list[str]:
    prompts: list[str] = []

    for metric in usage:
        if metric.status == "at_limit":
            prompts.append(f"{metric.label} is at plan capacity. Upgrade to raise the limit.")
        elif metric.status == "warning":
            prompts.append(f"{metric.label} is nearing the current plan limit.")

    for feature in features:
        if not feature.enabled:
            prompts.append(f"{feature.label} is unavailable on {plan.name}. Upgrade to unlock it.")

    if not prompts and plan.code == DEFAULT_PLAN_CODE:
        prompts.append("Upgrade for more templates, active campaigns, and advanced analytics.")

    return prompts[:4]


def get_brand_billing_snapshot(db: Session, *, brand_id: int, user: User) -> BrandBillingSnapshotRead:
    context = get_brand_access_context(db, brand_id=brand_id, user_id=user.id)
    usage_counts = compute_brand_usage_counts(db, brand_id=brand_id)
    usage = build_usage_metrics(plan=context.plan, usage_counts=usage_counts)
    features = build_feature_access(plan=context.plan)
    available_plans = [
        _serialize_plan(plan)
        for plan in db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order.asc())).all()
    ]

    return BrandBillingSnapshotRead(
        brand_id=context.brand.id,
        brand_name=context.brand.name,
        current_user_role=context.membership.role,
        subscription=_serialize_subscription(context.subscription, plan=context.plan),
        current_plan=_serialize_plan(context.plan),
        available_plans=available_plans,
        usage=usage,
        features=features,
        upgrade_prompts=_build_upgrade_prompts(plan=context.plan, usage=usage, features=features),
        recent_plan_activity=_list_recent_plan_activity(db, brand_id=brand_id),
    )


def update_brand_subscription(db: Session, *, brand_id: int, payload: BrandSubscriptionUpdate, user: User) -> BrandBillingSnapshotRead:
    context = get_brand_access_context(db, brand_id=brand_id, user_id=user.id)
    require_role(
        context.membership.role,
        BRAND_MANAGEMENT_ROLES,
        "You do not have permission to change this brand plan.",
    )

    target_plan = _get_plan_by_code(db, code=payload.plan_code.strip().lower())
    subscription = context.subscription
    previous_plan = context.plan
    previous_interval = subscription.billing_interval
    if previous_plan.code == target_plan.code and previous_interval == payload.billing_interval:
        return get_brand_billing_snapshot(db, brand_id=brand_id, user=user)

    now = datetime.now(UTC)

    subscription.plan_id = target_plan.id
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.billing_interval = payload.billing_interval
    subscription.cancel_at_period_end = False
    subscription.current_period_start = now
    subscription.current_period_end = _period_end_for_interval(payload.billing_interval, start=now)
    subscription.plan_snapshot_json = _plan_snapshot(target_plan)
    subscription.plan = target_plan

    action = "subscription.plan_changed"
    if previous_plan.code == target_plan.code and previous_interval != payload.billing_interval:
        action = "subscription.updated"

    record_audit_log(
        db,
        brand_id=brand_id,
        actor_user_id=user.id,
        entity_type="brand_subscription",
        entity_id=subscription.id,
        action=action,
        metadata={
            "from_plan_code": previous_plan.code,
            "to_plan_code": target_plan.code,
            "from_interval": previous_interval.value,
            "to_interval": payload.billing_interval.value,
        },
    )

    db.commit()
    db.refresh(subscription)
    return get_brand_billing_snapshot(db, brand_id=brand_id, user=user)
