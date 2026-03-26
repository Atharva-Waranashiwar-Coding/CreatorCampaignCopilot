from datetime import datetime

from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead
from app.schemas.calendar_item import CalendarItemRead
from app.schemas.campaign_dependency import CampaignDependencyRead
from app.schemas.campaign_milestone import CampaignMilestoneRead
from app.schemas.campaign import CampaignRead
from app.schemas.campaign_asset import CampaignAssetRead
from app.schemas.content_brief import ContentBriefRead
from app.schemas.content_draft import ContentDraftRead, DraftWorkflowStageCount
from app.schemas.draft_workflow import DraftWorkflowRead
from app.schemas.draft_version import DraftVersionRead


class CampaignPlanningSummaryRead(BaseModel):
    total_drafts: int
    idea_count: int
    draft_count: int
    in_review_count: int
    approved_count: int
    scheduled_count: int
    published_count: int
    rejected_count: int
    next_planned_publish_at: datetime | None


class CampaignOverviewRead(BaseModel):
    campaign: CampaignRead
    draft_workflow: DraftWorkflowRead
    brief: ContentBriefRead | None
    drafts: list[ContentDraftRead]
    assets: list[CampaignAssetRead]
    milestones: list[CampaignMilestoneRead]
    dependencies: list[CampaignDependencyRead]
    recent_versions: list[DraftVersionRead]
    schedule: list[CalendarItemRead]
    status_breakdown: list[DraftWorkflowStageCount]
    planning_summary: CampaignPlanningSummaryRead
    activity_timeline: list[AuditLogRead]
