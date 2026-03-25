from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    brand_id: int
    actor_user_id: int
    actor_name: str | None = None
    entity_type: str
    entity_id: int
    action: str
    metadata: dict[str, Any]
    created_at: datetime
