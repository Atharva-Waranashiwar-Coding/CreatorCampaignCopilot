from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import MembershipStatus
from app.models.audit_log import AuditLog
from app.models.brand_membership import BrandMembership
from app.schemas.audit_log import AuditLogRead


def record_audit_log(
    db: Session,
    *,
    brand_id: int,
    actor_user_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    metadata: dict,
) -> AuditLog:
    audit_log = AuditLog(
        brand_id=brand_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        metadata_json=metadata,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def list_brand_audit_logs(db: Session, *, brand_id: int, user_id: int) -> list[AuditLogRead]:
    membership = db.scalar(
        select(BrandMembership).where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise PermissionError("You do not have access to this brand.")

    logs = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(AuditLog.brand_id == brand_id)
        .order_by(AuditLog.created_at.desc())
        .limit(20)
    ).all()
    return [
        AuditLogRead(
            id=log.id,
            brand_id=log.brand_id,
            actor_user_id=log.actor_user_id,
            actor_name=log.actor.full_name if log.actor else None,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            metadata=log.metadata_json,
            created_at=log.created_at,
        )
        for log in logs
    ]
