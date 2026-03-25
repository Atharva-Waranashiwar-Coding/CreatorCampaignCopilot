from pydantic import BaseModel

from app.schemas.audit_log import AuditLogRead


class DashboardSummary(BaseModel):
    brand_count: int
    project_count: int
    campaign_count: int
    active_campaign_count: int
    recent_activity: list[AuditLogRead]
