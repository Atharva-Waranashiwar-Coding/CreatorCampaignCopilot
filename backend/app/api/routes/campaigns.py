from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.schemas.campaign_workspace import CampaignOverviewRead
from app.services.campaigns import (
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_overview,
    list_campaigns,
    update_campaign,
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


@router.get("", response_model=list[CampaignRead])
def read_campaigns(
    brand_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CampaignRead]:
    return list_campaigns(db, user=current_user, brand_id=brand_id, project_id=project_id)


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign_route(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignRead:
    try:
        return create_campaign(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{campaign_id}/overview", response_model=CampaignOverviewRead)
def read_campaign_overview(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignOverviewRead:
    try:
        return get_campaign_overview(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{campaign_id}", response_model=CampaignRead)
def read_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignRead:
    try:
        return get_campaign(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update_campaign_route(
    campaign_id: int,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignRead:
    try:
        return update_campaign(db, campaign_id=campaign_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_route(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_campaign(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
