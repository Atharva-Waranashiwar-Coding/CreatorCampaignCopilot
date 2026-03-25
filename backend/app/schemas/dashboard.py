from datetime import date

from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead


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


class DashboardAnalytics(BaseModel):
    campaigns: DashboardCampaignAnalytics
    drafts: DashboardDraftAnalytics
    reviews: DashboardReviewAnalytics
    schedule: DashboardScheduleAnalytics
