from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import MembershipStatus
from app.models.brand_membership import BrandMembership
from app.models.tool_usage_log import ToolUsageLog
from app.models.user import User
from app.schemas.tool_usage_log import ToolUsageLogRead

logger = logging.getLogger(__name__)


def _compact_value(value: Any, *, max_string_length: int = 280, max_items: int = 12) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    if isinstance(value, str):
        if len(value) <= max_string_length:
            return value
        return f"{value[: max_string_length - 3].rstrip()}..."

    if isinstance(value, list):
        return [_compact_value(item, max_string_length=max_string_length, max_items=max_items) for item in value[:max_items]]

    if isinstance(value, tuple):
        return [_compact_value(item, max_string_length=max_string_length, max_items=max_items) for item in value[:max_items]]

    if isinstance(value, dict):
        items = list(value.items())[:max_items]
        return {
            str(key): _compact_value(item, max_string_length=max_string_length, max_items=max_items)
            for key, item in items
        }

    return value


def record_tool_usage(
    db: Session,
    *,
    tool_name: str,
    actor_user_id: int,
    brand_id: int | None,
    target_entity_type: str,
    target_entity_id: int | None,
    invocation_source: str,
    request_payload: dict[str, Any],
    result_summary: dict[str, Any],
    was_successful: bool,
    error_detail: str | None = None,
) -> ToolUsageLog:
    entry = ToolUsageLog(
        tool_name=tool_name,
        actor_user_id=actor_user_id,
        brand_id=brand_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        invocation_source=invocation_source,
        was_successful=was_successful,
        error_detail=error_detail,
        request_payload=_compact_value(request_payload),
        result_summary=_compact_value(result_summary),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def safe_record_tool_usage(
    db: Session,
    *,
    tool_name: str,
    actor_user_id: int,
    brand_id: int | None,
    target_entity_type: str,
    target_entity_id: int | None,
    invocation_source: str,
    request_payload: dict[str, Any],
    result_summary: dict[str, Any],
    was_successful: bool,
    error_detail: str | None = None,
) -> None:
    try:
        record_tool_usage(
            db,
            tool_name=tool_name,
            actor_user_id=actor_user_id,
            brand_id=brand_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            invocation_source=invocation_source,
            request_payload=request_payload,
            result_summary=result_summary,
            was_successful=was_successful,
            error_detail=error_detail,
        )
    except Exception:
        db.rollback()
        logger.exception("Failed to record helper tool usage for %s", tool_name)


def list_recent_tool_usage(db: Session, *, user: User, limit: int = 20) -> list[ToolUsageLogRead]:
    accessible_brand_ids = (
        select(BrandMembership.brand_id)
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .scalar_subquery()
    )
    logs = db.scalars(
        select(ToolUsageLog)
        .options(joinedload(ToolUsageLog.actor), joinedload(ToolUsageLog.brand))
        .where(
            or_(
                ToolUsageLog.brand_id.in_(accessible_brand_ids),
                and_(
                    ToolUsageLog.brand_id.is_(None),
                    ToolUsageLog.actor_user_id == user.id,
                ),
            )
        )
        .order_by(ToolUsageLog.created_at.desc())
        .limit(limit)
    ).all()

    return [
        ToolUsageLogRead(
            id=log.id,
            tool_name=log.tool_name,
            actor_user_id=log.actor_user_id,
            actor_name=log.actor.full_name if log.actor else None,
            brand_id=log.brand_id,
            brand_name=log.brand.name if log.brand else None,
            target_entity_type=log.target_entity_type,
            target_entity_id=log.target_entity_id,
            invocation_source=log.invocation_source,
            was_successful=log.was_successful,
            error_detail=log.error_detail,
            request_payload=log.request_payload,
            result_summary=log.result_summary,
            created_at=log.created_at,
        )
        for log in logs
    ]
