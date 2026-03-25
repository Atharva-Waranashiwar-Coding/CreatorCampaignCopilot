from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.enums import DraftStatus
from app.db.session import get_db
from app.models.user import User
from app.schemas.content_draft import ContentDraftCreate, ContentDraftRead, ContentDraftUpdate
from app.services.drafts import create_draft, delete_draft, get_draft, list_drafts, update_draft

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("", response_model=list[ContentDraftRead])
def read_drafts(
    campaign_id: int | None = None,
    platform: str | None = None,
    status: DraftStatus | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ContentDraftRead]:
    return list_drafts(
        db,
        user=current_user,
        campaign_id=campaign_id,
        platform=platform,
        status=status,
        search=search,
    )


@router.post("", response_model=ContentDraftRead, status_code=status.HTTP_201_CREATED)
def create_draft_route(
    payload: ContentDraftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return create_draft(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{draft_id}", response_model=ContentDraftRead)
def read_draft(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return get_draft(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{draft_id}", response_model=ContentDraftRead)
def update_draft_route(
    draft_id: int,
    payload: ContentDraftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentDraftRead:
    try:
        return update_draft(db, draft_id=draft_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_route(
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_draft(db, draft_id=draft_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
