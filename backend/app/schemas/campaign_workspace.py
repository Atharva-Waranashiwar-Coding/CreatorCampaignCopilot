from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead
from app.schemas.campaign import CampaignRead
from app.schemas.content_brief import ContentBriefRead
from app.schemas.content_draft import ContentDraftRead, DraftStatusCount


class CampaignOverviewRead(BaseModel):
    campaign: CampaignRead
    brief: ContentBriefRead | None
    drafts: list[ContentDraftRead]
    status_breakdown: list[DraftStatusCount]
    activity_timeline: list[AuditLogRead]
