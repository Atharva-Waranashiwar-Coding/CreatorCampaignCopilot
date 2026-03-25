from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AssignmentEntityType, AssignmentStatus, CampaignStatus, DraftReviewAction, DraftStatus, MembershipStatus
from app.models.audit_log import AuditLog
from app.models.assignment import Assignment
from app.models.brand_membership import BrandMembership
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.campaign_asset import CampaignAsset
from app.models.content_draft import ContentDraft
from app.models.content_template import ContentTemplate
from app.models.draft_review import DraftReview
from app.models.project import Project
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.dashboard import (
    DashboardAnalytics,
    DashboardCampaignAnalytics,
    DashboardCountBucket,
    DashboardDateBucket,
    DashboardDraftAnalytics,
    DashboardApprovalAnalytics,
    DashboardCampaignHealth,
    DashboardCampaignHealthReport,
    DashboardCampaignHealthSummary,
    DashboardContentMixAnalytics,
    DashboardMemberBucket,
    DashboardReviewAnalytics,
    DashboardRevisionCycleItem,
    DashboardScheduleAnalytics,
    DashboardStatusBottleneck,
    DashboardSummary,
    DashboardWorkloadAnalytics,
    DashboardHealthFactor,
)

HEALTH_MAX_SCORE = 100
HEALTH_LABELS = (
    ("healthy", 85),
    ("watch", 70),
    ("at_risk", 50),
    ("critical", 0),
)
HEALTH_FACTOR_RULES = {
    "overdue_drafts": {"label": "Overdue drafts", "penalty_per_item": 18, "penalty_cap": 36},
    "pending_approvals": {"label": "Pending approvals", "penalty_per_item": 8, "penalty_cap": 24},
    "missing_assets": {"label": "Missing assets", "penalty_per_item": 12, "penalty_cap": 12},
    "unassigned_work": {"label": "Unassigned work", "penalty_per_item": 6, "penalty_cap": 18},
    "upcoming_deadlines": {"label": "Upcoming deadline pressure", "penalty_per_item": 5, "penalty_cap": 15},
}


def _resolve_brand_scope(db: Session, *, user_id: int, brand_id: int | None = None) -> list[int]:
    brand_ids = db.scalars(
        select(BrandMembership.brand_id).where(
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    if brand_id is None:
        return brand_ids
    if brand_id not in brand_ids:
        raise PermissionError("You do not have access to this brand.")
    return [brand_id]


def _bucket_counts(items: Counter | dict, *, labels: dict[str, str], ordered_keys: list[str]) -> list[DashboardCountBucket]:
    return [
        DashboardCountBucket(
            key=key,
            label=labels[key],
            count=int(items.get(key, 0)),
        )
        for key in ordered_keys
    ]


def _empty_dashboard_analytics(*, interval: str) -> DashboardAnalytics:
    campaign_labels = {status.value: status.value.replace("_", " ").title() for status in CampaignStatus}
    draft_labels = {status.value: status.value.replace("_", " ").title() for status in DraftStatus}
    review_labels = {action: action.replace("_", " ").title() for action in ["commented", "submitted", "approved", "rejected", "resubmitted"]}

    return DashboardAnalytics(
        campaigns=DashboardCampaignAnalytics(
            total=0,
            active_count=0,
            by_status=_bucket_counts({}, labels=campaign_labels, ordered_keys=[status.value for status in CampaignStatus]),
        ),
        drafts=DashboardDraftAnalytics(
            total=0,
            pending_review_count=0,
            approved_count=0,
            by_status=_bucket_counts({}, labels=draft_labels, ordered_keys=[status.value for status in DraftStatus]),
        ),
        reviews=DashboardReviewAnalytics(
            pending_count=0,
            recent_window_days=14,
            recent_actions=_bucket_counts({}, labels=review_labels, ordered_keys=list(review_labels)),
        ),
        schedule=DashboardScheduleAnalytics(
            upcoming_count=0,
            overdue_count=0,
            upcoming_by_day=[],
        ),
        workload=DashboardWorkloadAnalytics(
            drafts_by_member=[],
            pending_reviews_by_reviewer=[],
            bottlenecks_by_status=[],
        ),
        approvals=DashboardApprovalAnalytics(
            average_review_time_hours=0,
            average_approval_time_hours=0,
            rejection_rate=0,
            decision_count=0,
            drafts_with_multiple_revision_cycles=[],
            multi_revision_draft_count=0,
        ),
        content_mix=DashboardContentMixAnalytics(
            interval=interval,
            by_platform=[],
            by_content_type=[],
            by_campaign_status=[],
            by_interval=[],
        ),
    )


def _round_metric(value: float) -> float:
    return round(value, 2)


def _campaign_health_label(score: int) -> str:
    for label, threshold in HEALTH_LABELS:
        if score >= threshold:
            return label
    return "critical"


def _health_factor(*, key: str, count: int, detail: str) -> DashboardHealthFactor | None:
    if count <= 0:
        return None

    rule = HEALTH_FACTOR_RULES[key]
    penalty = min(count * rule["penalty_per_item"], rule["penalty_cap"])
    return DashboardHealthFactor(
        key=key,
        label=str(rule["label"]),
        count=count,
        penalty=penalty,
        detail=detail,
    )


def _build_campaign_health(campaign: Campaign, *, now: datetime) -> DashboardCampaignHealth:
    upcoming_deadline_cutoff = now + timedelta(days=7)
    drafts = campaign.drafts
    asset_count = len(campaign.assets)
    open_assignments_by_draft_id = {
        draft.id: any(
            assignment.status == AssignmentStatus.OPEN
            and assignment.assignment_type in {AssignmentEntityType.DRAFT, AssignmentEntityType.REVIEW_TASK}
            for assignment in draft.assignments
        )
        for draft in drafts
    }

    overdue_draft_count = sum(
        1
        for draft in drafts
        if draft.planned_publish_at is not None
        and draft.planned_publish_at < now
        and draft.status != DraftStatus.PUBLISHED
    )
    pending_approval_count = sum(1 for draft in drafts if draft.status == DraftStatus.IN_REVIEW)
    missing_assets_count = 1 if drafts and asset_count == 0 else 0
    unassigned_work_count = sum(
        1
        for draft in drafts
        if draft.status != DraftStatus.PUBLISHED and not open_assignments_by_draft_id.get(draft.id, False)
    )
    upcoming_deadline_count = sum(
        1
        for draft in drafts
        if draft.planned_publish_at is not None
        and now <= draft.planned_publish_at <= upcoming_deadline_cutoff
        and draft.status not in {DraftStatus.APPROVED, DraftStatus.SCHEDULED, DraftStatus.PUBLISHED}
    )

    factors = [
        _health_factor(
            key="overdue_drafts",
            count=overdue_draft_count,
            detail="Drafts have planned publish dates in the past and still are not published.",
        ),
        _health_factor(
            key="pending_approvals",
            count=pending_approval_count,
            detail="Drafts are waiting on reviewer approval.",
        ),
        _health_factor(
            key="missing_assets",
            count=missing_assets_count,
            detail="The campaign has drafts in motion but no linked assets.",
        ),
        _health_factor(
            key="unassigned_work",
            count=unassigned_work_count,
            detail="Drafts are still active without an open draft or review-task assignment.",
        ),
        _health_factor(
            key="upcoming_deadlines",
            count=upcoming_deadline_count,
            detail="Drafts are approaching a publish date within 7 days and are not yet in a ready state.",
        ),
    ]
    health_factors = [factor for factor in factors if factor is not None]
    penalty_total = sum(factor.penalty for factor in health_factors)
    score = max(0, HEALTH_MAX_SCORE - penalty_total)
    next_deadline_at = min(
        (draft.planned_publish_at for draft in drafts if draft.planned_publish_at is not None),
        default=None,
    )

    return DashboardCampaignHealth(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        project_id=campaign.project_id,
        project_name=campaign.project.name,
        brand_id=campaign.project.brand_id,
        brand_name=campaign.project.brand.name,
        campaign_status=campaign.status.value if isinstance(campaign.status, CampaignStatus) else str(campaign.status),
        score=score,
        label=_campaign_health_label(score),
        penalty_total=penalty_total,
        draft_count=len(drafts),
        asset_count=asset_count,
        next_deadline_at=next_deadline_at,
        factors=health_factors,
    )


def get_dashboard_summary(db: Session, *, user: User, brand_id: int | None = None) -> DashboardSummary:
    brand_ids = _resolve_brand_scope(db, user_id=user.id, brand_id=brand_id)
    if not brand_ids:
        return DashboardSummary(
            brand_count=0,
            project_count=0,
            campaign_count=0,
            active_campaign_count=0,
            draft_count=0,
            pending_review_count=0,
            approved_draft_count=0,
            scheduled_item_count=0,
            template_count=0,
            recent_activity=[],
        )

    project_count = db.scalar(select(func.count(Project.id)).where(Project.brand_id.in_(brand_ids))) or 0
    campaign_count = db.scalar(
        select(func.count(Campaign.id)).join(Project, Project.id == Campaign.project_id).where(Project.brand_id.in_(brand_ids))
    ) or 0
    active_campaign_count = db.scalar(
        select(func.count(Campaign.id))
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id.in_(brand_ids),
            Campaign.status == CampaignStatus.ACTIVE,
        )
    ) or 0
    draft_count = db.scalar(
        select(func.count(ContentDraft.id))
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
    ) or 0
    pending_review_count = db.scalar(
        select(func.count(ContentDraft.id))
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id.in_(brand_ids),
            ContentDraft.status == DraftStatus.IN_REVIEW,
        )
    ) or 0
    approved_draft_count = db.scalar(
        select(func.count(ContentDraft.id))
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id.in_(brand_ids),
            ContentDraft.status == DraftStatus.APPROVED,
        )
    ) or 0
    scheduled_item_count = db.scalar(
        select(func.count(CalendarItem.id)).where(
            CalendarItem.brand_id.in_(brand_ids),
            CalendarItem.scheduled_for >= datetime.now(UTC),
        )
    ) or 0
    template_count = db.scalar(
        select(func.count(ContentTemplate.id)).where(ContentTemplate.brand_id.in_(brand_ids))
    ) or 0

    recent_logs = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(AuditLog.brand_id.in_(brand_ids))
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    ).all()

    return DashboardSummary(
        brand_count=len(brand_ids),
        project_count=project_count,
        campaign_count=campaign_count,
        active_campaign_count=active_campaign_count,
        draft_count=draft_count,
        pending_review_count=pending_review_count,
        approved_draft_count=approved_draft_count,
        scheduled_item_count=scheduled_item_count,
        template_count=template_count,
        recent_activity=[
            AuditLogRead(
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
            for log in recent_logs
        ],
    )


def get_dashboard_analytics(
    db: Session,
    *,
    user: User,
    brand_id: int | None = None,
    interval: str = "month",
) -> DashboardAnalytics:
    brand_ids = _resolve_brand_scope(db, user_id=user.id, brand_id=brand_id)
    normalized_interval = interval.lower().strip()
    if normalized_interval not in {"week", "month"}:
        raise ValueError("Interval must be either 'week' or 'month'.")
    if not brand_ids:
        return _empty_dashboard_analytics(interval=normalized_interval)

    campaign_rows = db.execute(
        select(Campaign.status, func.count(Campaign.id))
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(Campaign.status)
    ).all()
    campaign_counts = Counter({status.value if isinstance(status, CampaignStatus) else str(status): count for status, count in campaign_rows})

    draft_rows = db.execute(
        select(ContentDraft.status, func.count(ContentDraft.id))
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(ContentDraft.status)
    ).all()
    draft_counts = Counter({status.value if isinstance(status, DraftStatus) else str(status): count for status, count in draft_rows})

    review_window_days = 14
    review_window_start = datetime.now(UTC) - timedelta(days=review_window_days)
    review_rows = db.execute(
        select(DraftReview.action, func.count(DraftReview.id))
        .join(ContentDraft, ContentDraft.id == DraftReview.draft_id)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id.in_(brand_ids),
            DraftReview.created_at >= review_window_start,
        )
        .group_by(DraftReview.action)
    ).all()
    review_counts = Counter({str(action): count for action, count in review_rows})

    now = datetime.now(UTC)
    upcoming_window_end = now + timedelta(days=14)
    upcoming_schedule_rows = db.scalars(
        select(CalendarItem.scheduled_for).where(
            CalendarItem.brand_id.in_(brand_ids),
            CalendarItem.scheduled_for >= now,
            CalendarItem.scheduled_for < upcoming_window_end,
        )
    ).all()
    upcoming_by_day = Counter(item.date() for item in upcoming_schedule_rows)
    overdue_count = db.scalar(
        select(func.count(CalendarItem.id)).where(
            CalendarItem.brand_id.in_(brand_ids),
            CalendarItem.scheduled_for < now,
            or_(
                CalendarItem.status.is_(None),
                CalendarItem.status != DraftStatus.PUBLISHED.value,
            ),
        )
    ) or 0

    campaign_labels = {status.value: status.value.replace("_", " ").title() for status in CampaignStatus}
    draft_labels = {status.value: status.value.replace("_", " ").title() for status in DraftStatus}
    review_keys = ["commented", "submitted", "approved", "rejected", "resubmitted"]
    review_labels = {key: key.replace("_", " ").title() for key in review_keys}

    now = datetime.now(UTC)
    due_soon_cutoff = now + timedelta(days=7)

    open_draft_assignment_rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.email,
            func.count(Assignment.id),
            func.sum(case((Assignment.due_at.is_not(None), case((Assignment.due_at < now, 1), else_=0)), else_=0)),
            func.sum(
                case(
                    (
                        Assignment.due_at.is_not(None),
                        case((Assignment.due_at >= now, case((Assignment.due_at <= due_soon_cutoff, 1), else_=0)), else_=0),
                    ),
                    else_=0,
                )
            ),
        )
        .join(User, User.id == Assignment.assignee_user_id)
        .where(
            Assignment.brand_id.in_(brand_ids),
            Assignment.assignment_type == AssignmentEntityType.DRAFT,
            Assignment.status == AssignmentStatus.OPEN,
        )
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.count(Assignment.id).desc(), User.full_name.asc())
    ).all()

    pending_review_rows = db.execute(
        select(
            User.id,
            User.full_name,
            User.email,
            func.count(Assignment.id),
            func.sum(case((Assignment.due_at.is_not(None), case((Assignment.due_at < now, 1), else_=0)), else_=0)),
            func.sum(
                case(
                    (
                        Assignment.due_at.is_not(None),
                        case((Assignment.due_at >= now, case((Assignment.due_at <= due_soon_cutoff, 1), else_=0)), else_=0),
                    ),
                    else_=0,
                )
            ),
        )
        .join(User, User.id == Assignment.assignee_user_id)
        .where(
            Assignment.brand_id.in_(brand_ids),
            Assignment.assignment_type == AssignmentEntityType.REVIEW_TASK,
            Assignment.status == AssignmentStatus.OPEN,
        )
        .group_by(User.id, User.full_name, User.email)
        .order_by(func.count(Assignment.id).desc(), User.full_name.asc())
    ).all()

    stale_cutoff = now - timedelta(days=3)
    bottleneck_rows = db.execute(
        select(
            ContentDraft.status,
            func.count(ContentDraft.id),
            func.sum(case((ContentDraft.updated_at < stale_cutoff, 1), else_=0)),
        )
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(ContentDraft.status)
    ).all()

    review_cycle_rows = db.execute(
        select(
            DraftReview.draft_id,
            DraftReview.action,
            DraftReview.created_at,
            ContentDraft.title,
            ContentDraft.status,
            Campaign.id,
            Campaign.name,
        )
        .join(ContentDraft, ContentDraft.id == DraftReview.draft_id)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .order_by(DraftReview.draft_id.asc(), DraftReview.created_at.asc())
    ).all()

    review_durations_hours: list[float] = []
    approval_durations_hours: list[float] = []
    decision_count = 0
    rejection_count = 0
    draft_revision_cycle_meta: dict[int, dict[str, object]] = {}
    pending_started_at_by_draft: dict[int, datetime] = {}

    for draft_id, action, created_at, draft_title, draft_status, campaign_id, campaign_name in review_cycle_rows:
        action_value = action.value if isinstance(action, DraftReviewAction) else str(action)
        status_value = draft_status if isinstance(draft_status, DraftStatus) else DraftStatus(str(draft_status))
        draft_meta = draft_revision_cycle_meta.setdefault(
            draft_id,
            {
                "draft_id": draft_id,
                "draft_title": draft_title,
                "campaign_id": campaign_id,
                "campaign_name": campaign_name,
                "revision_cycle_count": 0,
                "rejection_count": 0,
                "status": status_value,
            },
        )

        if action_value in {DraftReviewAction.SUBMITTED.value, DraftReviewAction.RESUBMITTED.value}:
            draft_meta["revision_cycle_count"] = int(draft_meta["revision_cycle_count"]) + 1
            pending_started_at_by_draft[draft_id] = created_at
            continue

        if action_value not in {DraftReviewAction.APPROVED.value, DraftReviewAction.REJECTED.value}:
            continue

        pending_started_at = pending_started_at_by_draft.pop(draft_id, None)
        if pending_started_at is None:
            continue

        elapsed_hours = (created_at - pending_started_at).total_seconds() / 3600
        review_durations_hours.append(elapsed_hours)
        decision_count += 1

        if action_value == DraftReviewAction.APPROVED.value:
            approval_durations_hours.append(elapsed_hours)
        else:
            rejection_count += 1
            draft_meta["rejection_count"] = int(draft_meta["rejection_count"]) + 1

    platform_rows = db.execute(
        select(ContentDraft.platform, func.count(ContentDraft.id))
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(ContentDraft.platform)
        .order_by(func.count(ContentDraft.id).desc(), ContentDraft.platform.asc())
    ).all()

    content_type_rows = db.execute(
        select(ContentDraft.content_type, func.count(ContentDraft.id))
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(ContentDraft.content_type)
        .order_by(func.count(ContentDraft.id).desc(), ContentDraft.content_type.asc())
    ).all()

    campaign_status_mix_rows = db.execute(
        select(Campaign.status, func.count(ContentDraft.id))
        .join(ContentDraft, ContentDraft.campaign_id == Campaign.id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(Campaign.status)
    ).all()

    interval_bucket_rows = db.execute(
        select(
            func.date_trunc(normalized_interval, ContentDraft.created_at),
            func.count(ContentDraft.id),
        )
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .where(Project.brand_id.in_(brand_ids))
        .group_by(func.date_trunc(normalized_interval, ContentDraft.created_at))
        .order_by(func.date_trunc(normalized_interval, ContentDraft.created_at).asc())
    ).all()

    return DashboardAnalytics(
        campaigns=DashboardCampaignAnalytics(
            total=sum(campaign_counts.values()),
            active_count=campaign_counts.get(CampaignStatus.ACTIVE.value, 0),
            by_status=_bucket_counts(
                campaign_counts,
                labels=campaign_labels,
                ordered_keys=[status.value for status in CampaignStatus],
            ),
        ),
        drafts=DashboardDraftAnalytics(
            total=sum(draft_counts.values()),
            pending_review_count=draft_counts.get(DraftStatus.IN_REVIEW.value, 0),
            approved_count=draft_counts.get(DraftStatus.APPROVED.value, 0),
            by_status=_bucket_counts(
                draft_counts,
                labels=draft_labels,
                ordered_keys=[status.value for status in DraftStatus],
            ),
        ),
        reviews=DashboardReviewAnalytics(
            pending_count=draft_counts.get(DraftStatus.IN_REVIEW.value, 0),
            recent_window_days=review_window_days,
            recent_actions=_bucket_counts(review_counts, labels=review_labels, ordered_keys=review_keys),
        ),
        schedule=DashboardScheduleAnalytics(
            upcoming_count=len(upcoming_schedule_rows),
            overdue_count=overdue_count,
            upcoming_by_day=[
                DashboardDateBucket(date=day, count=upcoming_by_day[day])
                for day in sorted(upcoming_by_day)
            ],
        ),
        workload=DashboardWorkloadAnalytics(
            drafts_by_member=[
                DashboardMemberBucket(
                    user_id=user_id,
                    name=name,
                    email=email,
                    count=int(count or 0),
                    overdue_count=int(overdue or 0),
                    due_soon_count=int(due_soon or 0),
                )
                for user_id, name, email, count, overdue, due_soon in open_draft_assignment_rows
            ],
            pending_reviews_by_reviewer=[
                DashboardMemberBucket(
                    user_id=user_id,
                    name=name,
                    email=email,
                    count=int(count or 0),
                    overdue_count=int(overdue or 0),
                    due_soon_count=int(due_soon or 0),
                )
                for user_id, name, email, count, overdue, due_soon in pending_review_rows
            ],
            bottlenecks_by_status=[
                DashboardStatusBottleneck(
                    status=status if isinstance(status, DraftStatus) else DraftStatus(str(status)),
                    label=(status.value if isinstance(status, DraftStatus) else str(status)).replace("_", " ").title(),
                    count=int(count or 0),
                    stale_count=int(stale_count or 0),
                )
                for status, count, stale_count in sorted(
                    bottleneck_rows,
                    key=lambda row: (-(row[1] or 0), str(row[0])),
                )
            ],
        ),
        approvals=DashboardApprovalAnalytics(
            average_review_time_hours=_round_metric(sum(review_durations_hours) / len(review_durations_hours)) if review_durations_hours else 0,
            average_approval_time_hours=_round_metric(sum(approval_durations_hours) / len(approval_durations_hours)) if approval_durations_hours else 0,
            rejection_rate=_round_metric((rejection_count / decision_count) * 100) if decision_count else 0,
            decision_count=decision_count,
            drafts_with_multiple_revision_cycles=[
                DashboardRevisionCycleItem(
                    draft_id=int(item["draft_id"]),
                    draft_title=str(item["draft_title"]),
                    campaign_id=int(item["campaign_id"]),
                    campaign_name=str(item["campaign_name"]),
                    revision_cycle_count=int(item["revision_cycle_count"]),
                    rejection_count=int(item["rejection_count"]),
                    status=item["status"] if isinstance(item["status"], DraftStatus) else DraftStatus(str(item["status"])),
                )
                for item in sorted(
                    (item for item in draft_revision_cycle_meta.values() if int(item["revision_cycle_count"]) > 1),
                    key=lambda item: (-int(item["revision_cycle_count"]), -int(item["rejection_count"]), str(item["draft_title"])),
                )[:8]
            ],
            multi_revision_draft_count=sum(1 for item in draft_revision_cycle_meta.values() if int(item["revision_cycle_count"]) > 1),
        ),
        content_mix=DashboardContentMixAnalytics(
            interval=normalized_interval,
            by_platform=[
                DashboardCountBucket(
                    key=platform,
                    label=platform,
                    count=int(count),
                )
                for platform, count in platform_rows
            ],
            by_content_type=[
                DashboardCountBucket(
                    key=content_type,
                    label=content_type,
                    count=int(count),
                )
                for content_type, count in content_type_rows
            ],
            by_campaign_status=[
                DashboardCountBucket(
                    key=status.value if isinstance(status, CampaignStatus) else str(status),
                    label=(status.value if isinstance(status, CampaignStatus) else str(status)).replace("_", " ").title(),
                    count=int(count),
                )
                for status, count in campaign_status_mix_rows
            ],
            by_interval=[
                DashboardDateBucket(date=bucket.date(), count=int(count))
                for bucket, count in interval_bucket_rows
                if bucket is not None
            ],
        ),
    )


def get_campaign_health_report(
    db: Session,
    *,
    user: User,
    brand_id: int | None = None,
) -> DashboardCampaignHealthReport:
    brand_ids = _resolve_brand_scope(db, user_id=user.id, brand_id=brand_id)
    if not brand_ids:
        return DashboardCampaignHealthReport(
            summary=DashboardCampaignHealthSummary(
                average_score=0,
                healthy_count=0,
                watch_count=0,
                at_risk_count=0,
                critical_count=0,
            ),
            campaigns=[],
        )

    campaigns = db.scalars(
        select(Campaign)
        .join(Project, Project.id == Campaign.project_id)
        .options(
            joinedload(Campaign.project).joinedload(Project.brand),
            joinedload(Campaign.assets),
            joinedload(Campaign.drafts).joinedload(ContentDraft.assignments),
        )
        .where(Project.brand_id.in_(brand_ids))
        .order_by(Campaign.updated_at.desc())
    ).unique().all()

    now = datetime.now(UTC)
    campaign_health = sorted(
        (_build_campaign_health(campaign, now=now) for campaign in campaigns),
        key=lambda item: (item.score, item.next_deadline_at or datetime.max.replace(tzinfo=UTC), item.campaign_name.lower()),
    )

    label_counts = Counter(item.label for item in campaign_health)
    average_score = _round_metric(sum(item.score for item in campaign_health) / len(campaign_health)) if campaign_health else 0

    return DashboardCampaignHealthReport(
        summary=DashboardCampaignHealthSummary(
            average_score=average_score,
            healthy_count=label_counts.get("healthy", 0),
            watch_count=label_counts.get("watch", 0),
            at_risk_count=label_counts.get("at_risk", 0),
            critical_count=label_counts.get("critical", 0),
        ),
        campaigns=campaign_health,
    )


def get_campaign_health_detail(
    db: Session,
    *,
    campaign_id: int,
    user: User,
) -> DashboardCampaignHealth:
    row = db.scalars(
        select(Campaign)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(Campaign.project).joinedload(Project.brand),
            joinedload(Campaign.assets),
            joinedload(Campaign.drafts).joinedload(ContentDraft.assignments),
        )
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).unique().first()

    if row is None:
        raise PermissionError("You do not have access to this campaign.")

    return _build_campaign_health(row, now=datetime.now(UTC))
