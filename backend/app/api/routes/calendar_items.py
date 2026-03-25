from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.calendar_item import CalendarItemCreate, CalendarItemRead, CalendarItemUpdate
from app.services.calendar_items import create_calendar_item, delete_calendar_item, list_calendar_items, update_calendar_item

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[CalendarItemRead])
def read_calendar_items(
    campaign_id: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CalendarItemRead]:
    return list_calendar_items(db, user=current_user, campaign_id=campaign_id, start=start, end=end)


@router.post("", response_model=CalendarItemRead, status_code=status.HTTP_201_CREATED)
def create_calendar_item_route(
    payload: CalendarItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarItemRead:
    try:
        return create_calendar_item(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{item_id}", response_model=CalendarItemRead)
def update_calendar_item_route(
    item_id: int,
    payload: CalendarItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalendarItemRead:
    try:
        return update_calendar_item(db, item_id=item_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calendar_item_route(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_calendar_item(db, item_id=item_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
