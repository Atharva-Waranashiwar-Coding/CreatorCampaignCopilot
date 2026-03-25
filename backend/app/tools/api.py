from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.tools.advanced_schemas import (
    AssetRecommendationRequest,
    AssetRecommendationResponse,
    BrandVoiceValidatorRequest,
    BrandVoiceValidatorResponse,
    CrossChannelAdaptationRequest,
    CrossChannelAdaptationResponse,
    ReviewFeedbackToRevisionChecklistRequest,
    ReviewFeedbackToRevisionChecklistResponse,
    TemplateRecommendationRequest,
    TemplateRecommendationResponse,
)
from app.tools.advanced_services import (
    asset_recommendation,
    brand_voice_validator,
    cross_channel_adaptation,
    review_feedback_to_revision_checklist,
    template_recommendation,
)
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
from app.tools.usage import safe_record_tool_usage

router = APIRouter()


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _resolve_invocation_source(request: Request) -> str:
    if request.headers.get("mcp-session-id") or request.headers.get("x-mcp-session-id"):
        return "mcp"
    return "rest"


def _target_from_context(
    *,
    draft_id: int | None,
    campaign_id: int | None,
    brand_id: int,
) -> tuple[str, int]:
    if draft_id is not None:
        return "content_draft", draft_id
    if campaign_id is not None:
        return "campaign", campaign_id
    return "brand", brand_id


@router.post(
    "/fetch-brand-guidelines",
    response_model=BrandGuidelinesResponse,
    operation_id="fetch_brand_guidelines",
    summary="Fetch brand guidelines",
    description="Return stored brand voice, audience, channel preferences, and guideline context for a brand.",
)
def fetch_brand_guidelines_route(
    payload: FetchBrandGuidelinesRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandGuidelinesResponse:
    try:
        result = fetch_brand_guidelines(db, brand_id=payload.brand_id, user=current_user)
        safe_record_tool_usage(
            db,
            tool_name="fetch_brand_guidelines",
            actor_user_id=current_user.id,
            brand_id=result.brand_id,
            target_entity_type="brand",
            target_entity_id=result.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="fetch_brand_guidelines",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="brand",
            target_entity_id=payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FetchTemplatesResponse:
    try:
        result = fetch_templates(db, payload=payload, user=current_user)
        safe_record_tool_usage(
            db,
            tool_name="fetch_templates",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="brand" if payload.brand_id is not None else "workspace",
            target_entity_id=payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="fetch_templates",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="brand" if payload.brand_id is not None else "workspace",
            target_entity_id=payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ValidateContentAgainstGuidelinesResponse:
    try:
        result = validate_content_against_guidelines(db, payload=payload, user=current_user)
        safe_record_tool_usage(
            db,
            tool_name="validate_content_against_guidelines",
            actor_user_id=current_user.id,
            brand_id=result.brand_id,
            target_entity_type="brand",
            target_entity_id=result.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="validate_content_against_guidelines",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="brand",
            target_entity_id=payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrieveCampaignAssetsResponse:
    try:
        result = retrieve_campaign_assets(db, payload=payload, user=current_user)
        safe_record_tool_usage(
            db,
            tool_name="retrieve_campaign_assets",
            actor_user_id=current_user.id,
            brand_id=result.brand_id,
            target_entity_type="campaign",
            target_entity_id=result.campaign_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="retrieve_campaign_assets",
            actor_user_id=current_user.id,
            brand_id=None,
            target_entity_type="campaign",
            target_entity_id=payload.campaign_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SummarizeReviewFeedbackResponse:
    try:
        result = summarize_review_feedback(db, payload=payload, user=current_user)
        safe_record_tool_usage(
            db,
            tool_name="summarize_review_feedback",
            actor_user_id=current_user.id,
            brand_id=result.brand_id,
            target_entity_type="content_draft",
            target_entity_id=result.draft_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="summarize_review_feedback",
            actor_user_id=current_user.id,
            brand_id=None,
            target_entity_type="content_draft",
            target_entity_id=payload.draft_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
        _raise_service_error(exc)


@router.post(
    "/brand-voice-validator",
    response_model=BrandVoiceValidatorResponse,
    operation_id="brand_voice_validator",
    summary="Validate brand voice alignment",
    description="Score draft tone against stored brand voice cues and return structured revision guidance.",
)
def brand_voice_validator_route(
    payload: BrandVoiceValidatorRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BrandVoiceValidatorResponse:
    try:
        result = brand_voice_validator(db, payload=payload, user=current_user)
        target_entity_type, target_entity_id = _target_from_context(
            draft_id=result.context.draft_id,
            campaign_id=result.context.campaign_id,
            brand_id=result.context.brand_id,
        )
        safe_record_tool_usage(
            db,
            tool_name="brand_voice_validator",
            actor_user_id=current_user.id,
            brand_id=result.context.brand_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="brand_voice_validator",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="content_draft" if payload.draft_id is not None else "brand",
            target_entity_id=payload.draft_id if payload.draft_id is not None else payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
        _raise_service_error(exc)


@router.post(
    "/cross-channel-adaptation",
    response_model=CrossChannelAdaptationResponse,
    operation_id="cross_channel_adaptation",
    summary="Adapt copy across channels",
    description="Transform current draft copy for a target platform without mutating the base draft.",
)
def cross_channel_adaptation_route(
    payload: CrossChannelAdaptationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CrossChannelAdaptationResponse:
    try:
        result = cross_channel_adaptation(db, payload=payload, user=current_user)
        target_entity_type, target_entity_id = _target_from_context(
            draft_id=result.context.draft_id,
            campaign_id=result.context.campaign_id,
            brand_id=result.context.brand_id,
        )
        safe_record_tool_usage(
            db,
            tool_name="cross_channel_adaptation",
            actor_user_id=current_user.id,
            brand_id=result.context.brand_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="cross_channel_adaptation",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="content_draft" if payload.draft_id is not None else "brand",
            target_entity_id=payload.draft_id if payload.draft_id is not None else payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
        _raise_service_error(exc)


@router.post(
    "/template-recommendation",
    response_model=TemplateRecommendationResponse,
    operation_id="template_recommendation",
    summary="Recommend templates for a draft",
    description="Rank brand templates using current draft context and explain the strongest candidates.",
)
def template_recommendation_route(
    payload: TemplateRecommendationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TemplateRecommendationResponse:
    try:
        result = template_recommendation(db, payload=payload, user=current_user)
        target_entity_type, target_entity_id = _target_from_context(
            draft_id=result.context.draft_id,
            campaign_id=result.context.campaign_id,
            brand_id=result.context.brand_id,
        )
        safe_record_tool_usage(
            db,
            tool_name="template_recommendation",
            actor_user_id=current_user.id,
            brand_id=result.context.brand_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="template_recommendation",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="content_draft" if payload.draft_id is not None else "brand",
            target_entity_id=payload.draft_id if payload.draft_id is not None else payload.brand_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
        _raise_service_error(exc)


@router.post(
    "/asset-recommendation",
    response_model=AssetRecommendationResponse,
    operation_id="asset_recommendation",
    summary="Recommend assets for a draft",
    description="Rank available campaign assets against the draft context and platform-specific needs.",
)
def asset_recommendation_route(
    payload: AssetRecommendationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRecommendationResponse:
    try:
        result = asset_recommendation(db, payload=payload, user=current_user)
        target_entity_type, target_entity_id = _target_from_context(
            draft_id=result.context.draft_id,
            campaign_id=result.context.campaign_id,
            brand_id=result.context.brand_id,
        )
        safe_record_tool_usage(
            db,
            tool_name="asset_recommendation",
            actor_user_id=current_user.id,
            brand_id=result.context.brand_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="asset_recommendation",
            actor_user_id=current_user.id,
            brand_id=payload.brand_id,
            target_entity_type="content_draft" if payload.draft_id is not None else "campaign",
            target_entity_id=payload.draft_id if payload.draft_id is not None else payload.campaign_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
        _raise_service_error(exc)


@router.post(
    "/review-feedback-to-revision-checklist",
    response_model=ReviewFeedbackToRevisionChecklistResponse,
    operation_id="review_feedback_to_revision_checklist",
    summary="Convert review feedback into a revision checklist",
    description="Turn recent review comments into structured, prioritized revision steps for the current draft.",
)
def review_feedback_to_revision_checklist_route(
    payload: ReviewFeedbackToRevisionChecklistRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewFeedbackToRevisionChecklistResponse:
    try:
        result = review_feedback_to_revision_checklist(db, payload=payload, user=current_user)
        safe_record_tool_usage(
            db,
            tool_name="review_feedback_to_revision_checklist",
            actor_user_id=current_user.id,
            brand_id=result.context.brand_id,
            target_entity_type="content_draft",
            target_entity_id=result.context.draft_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary=result.model_dump(mode="json"),
            was_successful=True,
        )
        return result
    except Exception as exc:
        safe_record_tool_usage(
            db,
            tool_name="review_feedback_to_revision_checklist",
            actor_user_id=current_user.id,
            brand_id=None,
            target_entity_type="content_draft",
            target_entity_id=payload.draft_id,
            invocation_source=_resolve_invocation_source(request),
            request_payload=payload.model_dump(mode="json"),
            result_summary={},
            was_successful=False,
            error_detail=str(exc),
        )
        _raise_service_error(exc)
