from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentRead
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.schemas.campaign_asset import CampaignAssetCreate, CampaignAssetRead, CampaignAssetUpdate
from app.schemas.campaign_milestone import CampaignMilestoneRead, CampaignMilestoneUpdate
from app.schemas.campaign_workspace import CampaignOverviewRead
from app.schemas.collaboration_comment import CollaborationCommentCreate, CollaborationCommentRead
from app.services.assignments import create_campaign_assignment, list_campaign_assignments
from app.services.assets import (
    create_campaign_asset,
    delete_campaign_asset,
    list_campaign_assets,
    update_campaign_asset,
)
from app.services.campaigns import (
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_overview,
    list_campaigns,
    update_campaign,
)
from app.services.campaign_milestones import list_campaign_milestones, update_campaign_milestone
from app.services.comments import create_campaign_comment, list_campaign_comments

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


@router.get("/{campaign_id}/milestones", response_model=list[CampaignMilestoneRead])
def read_campaign_milestones(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CampaignMilestoneRead]:
    try:
        return list_campaign_milestones(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{campaign_id}/milestones/{milestone_id}", response_model=CampaignMilestoneRead)
def update_campaign_milestone_route(
    campaign_id: int,
    milestone_id: int,
    payload: CampaignMilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignMilestoneRead:
    try:
        return update_campaign_milestone(
            db,
            campaign_id=campaign_id,
            milestone_id=milestone_id,
            payload=payload,
            user=current_user,
        )
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{campaign_id}/comments", response_model=list[CollaborationCommentRead])
def read_campaign_comments(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollaborationCommentRead]:
    try:
        return list_campaign_comments(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{campaign_id}/comments", response_model=list[CollaborationCommentRead], status_code=status.HTTP_201_CREATED)
def create_campaign_comment_route(
    campaign_id: int,
    payload: CollaborationCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CollaborationCommentRead]:
    try:
        return create_campaign_comment(db, campaign_id=campaign_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{campaign_id}/assignments", response_model=list[AssignmentRead])
def read_campaign_assignments(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentRead]:
    try:
        return list_campaign_assignments(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{campaign_id}/assignments", response_model=list[AssignmentRead], status_code=status.HTTP_201_CREATED)
def create_campaign_assignment_route(
    campaign_id: int,
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentRead]:
    try:
        return create_campaign_assignment(db, campaign_id=campaign_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/{campaign_id}/assets", response_model=list[CampaignAssetRead])
def read_campaign_assets(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CampaignAssetRead]:
    try:
        return list_campaign_assets(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post("/{campaign_id}/assets", response_model=CampaignAssetRead, status_code=status.HTTP_201_CREATED)
def create_campaign_asset_route(
    campaign_id: int,
    payload: CampaignAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignAssetRead:
    try:
        return create_campaign_asset(db, campaign_id=campaign_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.patch("/{campaign_id}/assets/{asset_id}", response_model=CampaignAssetRead)
def update_campaign_asset_route(
    campaign_id: int,
    asset_id: int,
    payload: CampaignAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CampaignAssetRead:
    try:
        return update_campaign_asset(db, campaign_id=campaign_id, asset_id=asset_id, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.delete("/{campaign_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign_asset_route(
    campaign_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        delete_campaign_asset(db, campaign_id=campaign_id, asset_id=asset_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
