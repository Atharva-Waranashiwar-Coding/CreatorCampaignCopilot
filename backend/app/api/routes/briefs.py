from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.content_brief import ContentBriefCreate, ContentBriefRead, ContentBriefUpdate
from app.services.briefs import delete_campaign_brief, get_campaign_brief, upsert_campaign_brief

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/campaigns/{campaign_id}/brief", response_model=ContentBriefRead | None)
def read_campaign_brief(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentBriefRead | None:
    try:
        return get_campaign_brief(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.put("/campaigns/{campaign_id}/brief", response_model=ContentBriefRead)
def upsert_campaign_brief_route(
    campaign_id: int,
    payload: ContentBriefCreate | ContentBriefUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContentBriefRead:
    try:
        return upsert_campaign_brief(db, campaign_id=campaign_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/campaigns/{campaign_id}/brief", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_brief_route(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_campaign_brief(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
