from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationMarkAllRead, NotificationRead, NotificationSummaryRead
from app.services.notifications import (
    get_notification_summary,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[NotificationRead])
def read_notifications(
    unread_only: bool = False,
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationRead]:
    try:
        return list_notifications(db, user=current_user, unread_only=unread_only, limit=limit)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/summary", response_model=NotificationSummaryRead)
def read_notification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationSummaryRead:
    try:
        return get_notification_summary(db, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read_route(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationRead:
    try:
        return mark_notification_read(db, notification_id=notification_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/read-all", response_model=NotificationMarkAllRead)
def mark_all_notifications_read_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationMarkAllRead:
    try:
        return NotificationMarkAllRead(updated_count=mark_all_notifications_read(db, user=current_user))
    except Exception as exc:
        _raise_service_error(exc)
