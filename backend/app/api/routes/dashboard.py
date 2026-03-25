from fastapi import APIRouter, Depends
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardAnalytics, DashboardCampaignHealth, DashboardCampaignHealthReport, DashboardSummary
from app.services.dashboard import (
    get_campaign_health_detail,
    get_campaign_health_report,
    get_dashboard_analytics,
    get_dashboard_summary,
)

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


@router.get("/summary", response_model=DashboardSummary)
def read_dashboard_summary(
    brand_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummary:
    try:
        return get_dashboard_summary(db, user=current_user, brand_id=brand_id)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/analytics", response_model=DashboardAnalytics)
def read_dashboard_analytics(
    brand_id: int | None = None,
    interval: str = "month",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardAnalytics:
    try:
        return get_dashboard_analytics(db, user=current_user, brand_id=brand_id, interval=interval)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/campaign-health", response_model=DashboardCampaignHealthReport)
def read_campaign_health_report(
    brand_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardCampaignHealthReport:
    try:
        return get_campaign_health_report(db, user=current_user, brand_id=brand_id)
    except Exception as exc:
        _raise_service_error(exc)


@router.get("/campaign-health/{campaign_id}", response_model=DashboardCampaignHealth)
def read_campaign_health_detail(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardCampaignHealth:
    try:
        return get_campaign_health_detail(db, campaign_id=campaign_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
