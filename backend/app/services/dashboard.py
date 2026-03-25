from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import CampaignStatus, DraftStatus, MembershipStatus
from app.models.audit_log import AuditLog
from app.models.brand_membership import BrandMembership
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
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
    DashboardReviewAnalytics,
    DashboardScheduleAnalytics,
    DashboardSummary,
)


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


def get_dashboard_analytics(db: Session, *, user: User, brand_id: int | None = None) -> DashboardAnalytics:
    brand_ids = _resolve_brand_scope(db, user_id=user.id, brand_id=brand_id)
    if not brand_ids:
        empty_buckets = {
            "campaigns": [status.value for status in CampaignStatus],
            "drafts": [status.value for status in DraftStatus],
        }
        campaign_labels = {status.value: status.value.replace("_", " ").title() for status in CampaignStatus}
        draft_labels = {status.value: status.value.replace("_", " ").title() for status in DraftStatus}
        review_labels = {action: action.replace("_", " ").title() for action in ["commented", "submitted", "approved", "rejected", "resubmitted"]}
        return DashboardAnalytics(
            campaigns=DashboardCampaignAnalytics(
                total=0,
                active_count=0,
                by_status=_bucket_counts({}, labels=campaign_labels, ordered_keys=empty_buckets["campaigns"]),
            ),
            drafts=DashboardDraftAnalytics(
                total=0,
                pending_review_count=0,
                approved_count=0,
                by_status=_bucket_counts({}, labels=draft_labels, ordered_keys=empty_buckets["drafts"]),
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
        )

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
    )
