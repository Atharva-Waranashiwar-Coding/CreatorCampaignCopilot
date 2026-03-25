from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.tools.schemas import (
    BrandGuidelinesResponse,
    FetchBrandGuidelinesRequest,
    FetchTemplatesRequest,
    FetchTemplatesResponse,
    RetrieveCampaignAssetsRequest,
    RetrieveCampaignAssetsResponse,
    SummarizeReviewFeedbackRequest,
    SummarizeReviewFeedbackResponse,
    ValidateContentAgainstGuidelinesRequest,
    ValidateContentAgainstGuidelinesResponse,
)
from app.tools.services import (
    fetch_brand_guidelines,
    fetch_templates,
    retrieve_campaign_assets,
    summarize_review_feedback,
    validate_content_against_guidelines,
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


@router.post(
    "/fetch-brand-guidelines",
    response_model=BrandGuidelinesResponse,
    operation_id="fetch_brand_guidelines",
    summary="Fetch brand guidelines",
    description="Return stored brand voice, audience, channel preferences, and guideline context for a brand.",
)
def fetch_brand_guidelines_route(
    payload: FetchBrandGuidelinesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandGuidelinesResponse:
    try:
        return fetch_brand_guidelines(db, brand_id=payload.brand_id, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post(
    "/fetch-templates",
    response_model=FetchTemplatesResponse,
    operation_id="fetch_templates",
    summary="Fetch templates",
    description="Return accessible content templates filtered by brand, platform, content type, and search terms.",
)
def fetch_templates_route(
    payload: FetchTemplatesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FetchTemplatesResponse:
    try:
        return fetch_templates(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post(
    "/validate-content-against-guidelines",
    response_model=ValidateContentAgainstGuidelinesResponse,
    operation_id="validate_content_against_guidelines",
    summary="Validate content against brand guidelines",
    description="Check draft copy against stored brand guidance and an optional brand template using deterministic validation signals.",
)
def validate_content_against_guidelines_route(
    payload: ValidateContentAgainstGuidelinesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidateContentAgainstGuidelinesResponse:
    try:
        return validate_content_against_guidelines(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post(
    "/retrieve-campaign-assets",
    response_model=RetrieveCampaignAssetsResponse,
    operation_id="retrieve_campaign_assets",
    summary="Retrieve campaign assets",
    description="Return asset references for an accessible campaign, optionally filtered by asset type or free-text search.",
)
def retrieve_campaign_assets_route(
    payload: RetrieveCampaignAssetsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrieveCampaignAssetsResponse:
    try:
        return retrieve_campaign_assets(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)


@router.post(
    "/summarize-review-feedback",
    response_model=SummarizeReviewFeedbackResponse,
    operation_id="summarize_review_feedback",
    summary="Summarize review feedback",
    description="Summarize the draft review thread into approval notes, blockers, recent comments, and action counts.",
)
def summarize_review_feedback_route(
    payload: SummarizeReviewFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummarizeReviewFeedbackResponse:
    try:
        return summarize_review_feedback(db, payload=payload, user=current_user)
    except Exception as exc:
        _raise_service_error(exc)
