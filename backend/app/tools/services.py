from __future__ import annotations

import re
from collections import Counter

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.campaign_asset import CampaignAssetRead
from app.schemas.content_template import ContentTemplateRead
from app.services.assets import list_campaign_assets
from app.services.brands import get_brand
from app.services.campaigns import get_campaign
from app.services.drafts import get_draft
from app.services.reviews import get_draft_review_thread
from app.services.templates import get_template, list_templates
from app.tools.schemas import (
    BrandGuidelinesResponse,
    CampaignAssetSummary,
    FetchTemplatesRequest,
    FetchTemplatesResponse,
    ReviewActionCount,
    ReviewCommentSummary,
    RetrieveCampaignAssetsRequest,
    RetrieveCampaignAssetsResponse,
    SummarizeReviewFeedbackRequest,
    SummarizeReviewFeedbackResponse,
    TemplateFilterSet,
    TemplateSummary,
    ValidateContentAgainstGuidelinesRequest,
    ValidateContentAgainstGuidelinesResponse,
    ValidationCheckResult,
)

STOPWORDS = {
    "about",
    "after",
    "against",
    "also",
    "because",
    "before",
    "between",
    "campaign",
    "content",
    "could",
    "draft",
    "from",
    "have",
    "into",
    "just",
    "more",
    "should",
    "that",
    "their",
    "them",
    "there",
    "these",
    "this",
    "with",
    "would",
    "your",
}


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _extract_keywords(*values: str | None, limit: int = 12) -> list[str]:
    keywords: list[str] = []

    for value in values:
        for token in re.findall(r"[a-z0-9]{4,}", (value or "").lower()):
            if token in STOPWORDS or token in keywords:
                continue
            keywords.append(token)
            if len(keywords) >= limit:
                return keywords

    return keywords


def _excerpt(value: str | None, *, limit: int = 180) -> str:
    normalized = _normalize_text(value)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


def fetch_brand_guidelines(db: Session, *, brand_id: int, user: User) -> BrandGuidelinesResponse:
    brand = get_brand(db, brand_id=brand_id, user=user)
    guidance_points = [
        _normalize_text(brand.guidelines_summary),
        _normalize_text(brand.tone_of_voice),
        _normalize_text(brand.target_audience),
    ]
    guidance_points.extend(channel.strip() for channel in brand.preferred_channels if channel.strip())

    return BrandGuidelinesResponse(
        brand_id=brand.id,
        brand_name=brand.name,
        slug=brand.slug,
        current_user_role=brand.current_user_role,
        industry=brand.industry,
        description=brand.description,
        tone_of_voice=brand.tone_of_voice,
        target_audience=brand.target_audience,
        preferred_channels=brand.preferred_channels,
        guidelines_summary=brand.guidelines_summary,
        project_count=brand.project_count,
        campaign_count=brand.campaign_count,
        guidance_points=[point for point in guidance_points if point],
    )


def _matches_template(
    template: ContentTemplateRead,
    *,
    platform: str | None,
    content_type: str | None,
) -> bool:
    if platform and template.platform and template.platform.lower() != platform.lower():
        return False
    if content_type and template.content_type and template.content_type.lower() != content_type.lower():
        return False
    return True


def fetch_templates(
    db: Session,
    *,
    payload: FetchTemplatesRequest,
    user: User,
) -> FetchTemplatesResponse:
    templates = list_templates(
        db,
        user=user,
        brand_id=payload.brand_id,
        template_type=payload.template_type,
        search=payload.search,
    )
    filtered = [
        template
        for template in templates
        if _matches_template(
            template,
            platform=payload.platform,
            content_type=payload.content_type,
        )
    ]
    selected = filtered[: payload.limit]

    return FetchTemplatesResponse(
        filters=TemplateFilterSet(
            brand_id=payload.brand_id,
            template_type=payload.template_type,
            platform=payload.platform,
            content_type=payload.content_type,
            search=payload.search,
            limit=payload.limit,
        ),
        total=len(filtered),
        returned=len(selected),
        templates=[
            TemplateSummary(
                id=template.id,
                brand_id=template.brand_id,
                brand_name=template.brand_name,
                name=template.name,
                description=template.description,
                template_type=template.template_type,
                platform=template.platform,
                content_type=template.content_type,
                excerpt=_excerpt(template.body),
                updated_at=template.updated_at,
            )
            for template in selected
        ],
    )


def validate_content_against_guidelines(
    db: Session,
    *,
    payload: ValidateContentAgainstGuidelinesRequest,
    user: User,
) -> ValidateContentAgainstGuidelinesResponse:
    brand = fetch_brand_guidelines(db, brand_id=payload.brand_id, user=user)
    content_text = " ".join(part for part in [payload.title, payload.content_body] if part)
    content_keywords = set(_extract_keywords(content_text, limit=32))
    brand_keywords = _extract_keywords(
        brand.guidelines_summary,
        brand.tone_of_voice,
        brand.target_audience,
        brand.description,
    )

    matched_keywords = [keyword for keyword in brand_keywords if keyword in content_keywords]
    missing_keywords = [keyword for keyword in brand_keywords if keyword not in content_keywords]

    checks: list[ValidationCheckResult] = []
    score = 100

    if len(payload.content_body.split()) < 20:
        score -= 20
        checks.append(
            ValidationCheckResult(
                check="content_length",
                status="warn",
                detail="Content is short for a brand review and may lack enough context or CTA detail.",
            )
        )
    else:
        checks.append(
            ValidationCheckResult(
                check="content_length",
                status="pass",
                detail="Content length is substantial enough for guideline review.",
            )
        )

    if payload.platform and brand.preferred_channels:
        if payload.platform.lower() in {channel.lower() for channel in brand.preferred_channels}:
            checks.append(
                ValidationCheckResult(
                    check="preferred_channel_alignment",
                    status="pass",
                    detail=f"Platform '{payload.platform}' is listed in the brand's preferred channels.",
                )
            )
        else:
            score -= 30
            checks.append(
                ValidationCheckResult(
                    check="preferred_channel_alignment",
                    status="fail",
                    detail=(
                        f"Platform '{payload.platform}' is not in the preferred channel list: "
                        f"{', '.join(brand.preferred_channels)}."
                    ),
                )
            )
    else:
        checks.append(
            ValidationCheckResult(
                check="preferred_channel_alignment",
                status="warn",
                detail="Platform or preferred channel data is missing, so channel alignment could not be confirmed.",
            )
        )

    if brand_keywords:
        if len(matched_keywords) >= max(1, min(3, len(brand_keywords) // 3 or 1)):
            checks.append(
                ValidationCheckResult(
                    check="guideline_keyword_coverage",
                    status="pass",
                    detail=f"Content reflects brand context keywords including {', '.join(matched_keywords[:4])}.",
                )
            )
        else:
            score -= 20
            detail = "Content does not strongly reflect the stored brand guidance keywords."
            if missing_keywords:
                detail = f"{detail} Missing examples: {', '.join(missing_keywords[:4])}."
            checks.append(
                ValidationCheckResult(
                    check="guideline_keyword_coverage",
                    status="warn",
                    detail=detail,
                )
            )
    else:
        checks.append(
            ValidationCheckResult(
                check="guideline_keyword_coverage",
                status="warn",
                detail="No structured guideline keywords were available from the brand profile.",
            )
        )

    template_name: str | None = None
    if payload.template_id is not None:
        template = get_template(db, template_id=payload.template_id, user=user)
        template_name = template.name
        template_keywords = _extract_keywords(template.body, template.description, limit=10)
        template_matches = [keyword for keyword in template_keywords if keyword in content_keywords]
        if template.brand_id != payload.brand_id:
            score -= 25
            checks.append(
                ValidationCheckResult(
                    check="template_brand_alignment",
                    status="fail",
                    detail="Selected template belongs to a different brand than the content under review.",
                )
            )
        elif template_matches:
            checks.append(
                ValidationCheckResult(
                    check="template_structure_alignment",
                    status="pass",
                    detail=f"Content reflects template language including {', '.join(template_matches[:4])}.",
                )
            )
        else:
            score -= 15
            checks.append(
                ValidationCheckResult(
                    check="template_structure_alignment",
                    status="warn",
                    detail="Content does not appear to reuse the selected template's structure or vocabulary.",
                )
            )

    score = max(score, 0)
    passed = score >= 70 and not any(check.status == "fail" for check in checks)
    summary = (
        f"Validation {'passed' if passed else 'needs revision'} with score {score}/100. "
        f"Matched {len(matched_keywords)} brand keywords and flagged "
        f"{sum(1 for check in checks if check.status != 'pass')} review areas."
    )

    return ValidateContentAgainstGuidelinesResponse(
        brand_id=brand.brand_id,
        brand_name=brand.brand_name,
        template_id=payload.template_id,
        template_name=template_name,
        score=score,
        passed=passed,
        summary=summary,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        checks=checks,
    )


def retrieve_campaign_assets(
    db: Session,
    *,
    payload: RetrieveCampaignAssetsRequest,
    user: User,
) -> RetrieveCampaignAssetsResponse:
    campaign = get_campaign(db, campaign_id=payload.campaign_id, user=user)
    assets = list_campaign_assets(db, campaign_id=payload.campaign_id, user=user)
    filtered = [
        asset
        for asset in assets
        if _matches_asset(asset, asset_type=payload.asset_type, search=payload.search)
    ]

    return RetrieveCampaignAssetsResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        brand_id=campaign.brand_id,
        brand_name=campaign.brand_name,
        returned=len(filtered),
        assets=[_serialize_asset_summary(asset) for asset in filtered],
    )


def _matches_asset(
    asset: CampaignAssetRead,
    *,
    asset_type: str | None,
    search: str | None,
) -> bool:
    if asset_type and asset.asset_type.lower() != asset_type.lower():
        return False
    if search:
        haystack = " ".join(filter(None, [asset.name, asset.notes, asset.mime_type])).lower()
        if search.lower() not in haystack:
            return False
    return True


def _serialize_asset_summary(asset: CampaignAssetRead) -> CampaignAssetSummary:
    return CampaignAssetSummary(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type,
        file_url=asset.file_url,
        thumbnail_url=asset.thumbnail_url,
        mime_type=asset.mime_type,
        file_size_bytes=asset.file_size_bytes,
        notes=asset.notes,
        updated_at=asset.updated_at,
    )


def summarize_review_feedback(
    db: Session,
    *,
    payload: SummarizeReviewFeedbackRequest,
    user: User,
) -> SummarizeReviewFeedbackResponse:
    draft = get_draft(db, draft_id=payload.draft_id, user=user)
    review_thread = get_draft_review_thread(db, draft_id=payload.draft_id, user=user)
    reviews_with_comments = [review for review in review_thread.reviews if review.comment]
    comment_summaries = [
        ReviewCommentSummary(
            actor_name=review.actor_name,
            action=review.action,
            comment=review.comment or "",
            created_at=review.created_at,
        )
        for review in reviews_with_comments[: payload.limit]
    ]
    blockers = [
        review.comment or ""
        for review in reviews_with_comments
        if review.action == "rejected"
    ][: payload.limit]
    approvals = [
        review.comment or ""
        for review in reviews_with_comments
        if review.action == "approved"
    ][: payload.limit]
    action_counts = Counter(review.action for review in review_thread.reviews)
    latest_action = review_thread.reviews[0].action if review_thread.reviews else None
    summary_parts = [
        f"{len(review_thread.reviews)} review events recorded",
        f"latest action: {latest_action.value if latest_action else 'none'}",
    ]
    if blockers:
        summary_parts.append(f"{len(blockers)} blocker comments need attention")
    if approvals:
        summary_parts.append(f"{len(approvals)} approval notes captured")

    return SummarizeReviewFeedbackResponse(
        draft_id=draft.id,
        draft_title=draft.title,
        brand_id=draft.brand_id,
        brand_name=draft.brand_name,
        current_status=draft.status,
        current_status_label=draft.status_label,
        current_user_role=review_thread.current_user_role,
        review_count=len(review_thread.reviews),
        latest_action=latest_action,
        summary=". ".join(summary_parts).strip(".") + ".",
        blockers=blockers,
        approvals=approvals,
        action_counts=[
            ReviewActionCount(action=action, count=count)
            for action, count in sorted(action_counts.items(), key=lambda item: item[0].value)
        ],
        recent_comments=comment_summaries,
    )
