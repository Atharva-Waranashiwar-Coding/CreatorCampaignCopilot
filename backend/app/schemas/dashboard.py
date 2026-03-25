from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead
from app.schemas.content_draft import DraftStatus


class DashboardSummary(BaseModel):
    brand_count: int
    project_count: int
    campaign_count: int
    active_campaign_count: int
    draft_count: int = 0
    pending_review_count: int = 0
    approved_draft_count: int = 0
    scheduled_item_count: int = 0
    template_count: int = 0
    recent_activity: list[AuditLogRead]


class DashboardCountBucket(BaseModel):
    key: str
    label: str
    count: int


class DashboardDateBucket(BaseModel):
    date: date
    count: int


class DashboardHealthFactor(BaseModel):
    key: str
    label: str
    count: int
    penalty: int
    detail: str


class DashboardMemberBucket(BaseModel):
    user_id: int
    name: str
    email: str
    count: int
    overdue_count: int = 0
    due_soon_count: int = 0


class DashboardStatusBottleneck(BaseModel):
    status: DraftStatus
    label: str
    count: int
    stale_count: int


class DashboardCampaignAnalytics(BaseModel):
    total: int
    active_count: int
    by_status: list[DashboardCountBucket]


class DashboardDraftAnalytics(BaseModel):
    total: int
    pending_review_count: int
    approved_count: int
    by_status: list[DashboardCountBucket]


class DashboardReviewAnalytics(BaseModel):
    pending_count: int
    recent_window_days: int
    recent_actions: list[DashboardCountBucket]


class DashboardScheduleAnalytics(BaseModel):
    upcoming_count: int
    overdue_count: int
    upcoming_by_day: list[DashboardDateBucket]


class DashboardWorkloadAnalytics(BaseModel):
    drafts_by_member: list[DashboardMemberBucket]
    pending_reviews_by_reviewer: list[DashboardMemberBucket]
    bottlenecks_by_status: list[DashboardStatusBottleneck]


class DashboardRevisionCycleItem(BaseModel):
    draft_id: int
    draft_title: str
    campaign_id: int
    campaign_name: str
    revision_cycle_count: int
    rejection_count: int
    status: DraftStatus


class DashboardApprovalAnalytics(BaseModel):
    average_review_time_hours: float
    average_approval_time_hours: float
    rejection_rate: float
    decision_count: int
    drafts_with_multiple_revision_cycles: list[DashboardRevisionCycleItem]
    multi_revision_draft_count: int


class DashboardContentMixAnalytics(BaseModel):
    interval: str
    by_platform: list[DashboardCountBucket]
    by_content_type: list[DashboardCountBucket]
    by_campaign_status: list[DashboardCountBucket]
    by_interval: list[DashboardDateBucket]


class DashboardCampaignHealth(BaseModel):
    campaign_id: int
    campaign_name: str
    project_id: int
    project_name: str
    brand_id: int
    brand_name: str
    campaign_status: str
    score: int
    label: str
    penalty_total: int
    draft_count: int
    asset_count: int
    next_deadline_at: datetime | None
    factors: list[DashboardHealthFactor]


class DashboardCampaignHealthSummary(BaseModel):
    average_score: float
    healthy_count: int
    watch_count: int
    at_risk_count: int
    critical_count: int


class DashboardCampaignHealthReport(BaseModel):
    summary: DashboardCampaignHealthSummary
    campaigns: list[DashboardCampaignHealth]


class DashboardAnalytics(BaseModel):
    campaigns: DashboardCampaignAnalytics
    drafts: DashboardDraftAnalytics
    reviews: DashboardReviewAnalytics
    schedule: DashboardScheduleAnalytics
    workload: DashboardWorkloadAnalytics
    approvals: DashboardApprovalAnalytics
    content_mix: DashboardContentMixAnalytics
