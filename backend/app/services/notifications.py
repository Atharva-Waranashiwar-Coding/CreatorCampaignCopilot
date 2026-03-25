from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import AssignmentStatus, MembershipStatus, NotificationType
from app.models.assignment import Assignment
from app.models.brand_membership import BrandMembership
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationRead, NotificationSummaryRead


def _serialize_notification(notification: Notification) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        user_id=notification.user_id,
        brand_id=notification.brand_id,
        actor_user_id=notification.actor_user_id,
        actor_name=notification.actor.full_name if notification.actor else None,
        notification_type=NotificationType(notification.notification_type),
        title=notification.title,
        body=notification.body,
        entity_type=notification.entity_type,
        entity_id=notification.entity_id,
        metadata=notification.metadata_json,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


def create_notification(
    db: Session,
    *,
    user_id: int,
    brand_id: int,
    notification_type: NotificationType,
    title: str,
    body: str,
    entity_type: str,
    entity_id: int | None,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    if dedupe_key:
        existing = db.scalar(select(Notification.id).where(Notification.dedupe_key == dedupe_key))
        if existing is not None:
            return None

    notification = Notification(
        user_id=user_id,
        brand_id=brand_id,
        actor_user_id=actor_user_id,
        notification_type=notification_type.value,
        title=title.strip(),
        body=body.strip(),
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
        dedupe_key=dedupe_key,
    )
    db.add(notification)
    db.flush()
    return notification


def sync_due_soon_notifications(db: Session, *, user: User, window_hours: int = 48) -> None:
    due_soon_cutoff = datetime.now(UTC) + timedelta(hours=window_hours)
    assignments = db.scalars(
        select(Assignment)
        .options(joinedload(Assignment.assignee), joinedload(Assignment.assigned_by))
        .where(
            Assignment.assignee_user_id == user.id,
            Assignment.status == AssignmentStatus.OPEN,
            Assignment.due_at.is_not(None),
            Assignment.due_at <= due_soon_cutoff,
        )
    ).all()

    for assignment in assignments:
        create_notification(
            db,
            user_id=user.id,
            brand_id=assignment.brand_id,
            notification_type=NotificationType.DUE_SOON,
            title="Assignment due soon",
            body="One of your collaboration assignments is approaching its due date.",
            entity_type=assignment.assignment_type.value,
            entity_id=assignment.entity_id,
            actor_user_id=assignment.assigned_by_user_id,
            metadata={
                "assignment_id": assignment.id,
                "assignment_type": assignment.assignment_type.value,
                "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
            },
            dedupe_key=f"assignment:{assignment.id}:due_soon",
        )


def list_notifications(
    db: Session,
    *,
    user: User,
    unread_only: bool = False,
    limit: int = 30,
) -> list[NotificationRead]:
    sync_due_soon_notifications(db, user=user)
    db.commit()

    brand_ids = db.scalars(
        select(BrandMembership.brand_id).where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    if not brand_ids:
        return []

    query = (
        select(Notification)
        .options(joinedload(Notification.actor))
        .where(
            Notification.user_id == user.id,
            Notification.brand_id.in_(brand_ids),
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))

    return [_serialize_notification(item) for item in db.scalars(query).all()]


def get_notification_summary(db: Session, *, user: User) -> NotificationSummaryRead:
    notifications = list_notifications(db, user=user, unread_only=True, limit=5)
    unread_count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.brand_id.in_(
                select(BrandMembership.brand_id).where(
                    BrandMembership.user_id == user.id,
                    BrandMembership.status == MembershipStatus.ACTIVE,
                )
            ),
            Notification.read_at.is_(None),
        )
    ) or 0
    return NotificationSummaryRead(unread_count=unread_count, recent_unread=notifications)


def mark_notification_read(db: Session, *, notification_id: int, user: User) -> NotificationRead:
    notification = db.scalar(
        select(Notification)
        .options(joinedload(Notification.actor))
        .where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise LookupError("Notification not found.")

    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)

    return _serialize_notification(notification)


def mark_all_notifications_read(db: Session, *, user: User) -> int:
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    for notification in notifications:
        notification.read_at = datetime.now(UTC)
    db.commit()
    return len(notifications)
