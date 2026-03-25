from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ToolUsageLogRead(BaseModel):
    id: int
    tool_name: str
    actor_user_id: int
    actor_name: str | None = None
    brand_id: int | None = None
    brand_name: str | None = None
    campaign_id: int | None = None
    draft_id: int | None = None
    target_entity_type: str
    target_entity_id: int | None = None
    invocation_source: str
    was_successful: bool
    error_detail: str | None = None
    request_payload: dict[str, Any]
    result_summary: dict[str, Any]
    request_trace: dict[str, Any] | None = None
    result_trace: dict[str, Any] | None = None
    created_at: datetime
