from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead
from app.schemas.calendar_item import CalendarItemRead
from app.schemas.campaign import CampaignRead
from app.schemas.campaign_asset import CampaignAssetRead
from app.schemas.content_brief import ContentBriefRead
from app.schemas.content_draft import ContentDraftRead, DraftStatusCount
from app.schemas.draft_version import DraftVersionRead


class CampaignOverviewRead(BaseModel):
    campaign: CampaignRead
    brief: ContentBriefRead | None
    drafts: list[ContentDraftRead]
    assets: list[CampaignAssetRead]
    recent_versions: list[DraftVersionRead]
    schedule: list[CalendarItemRead]
    status_breakdown: list[DraftStatusCount]
    activity_timeline: list[AuditLogRead]
