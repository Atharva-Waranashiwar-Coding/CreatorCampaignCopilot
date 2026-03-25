from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead


class DashboardSummary(BaseModel):
    brand_count: int
    project_count: int
    campaign_count: int
    active_campaign_count: int
    draft_count: int = 0
    in_review_draft_count: int = 0
    recent_activity: list[AuditLogRead]
