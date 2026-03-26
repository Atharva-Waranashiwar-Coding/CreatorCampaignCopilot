from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.core.enums import DraftReviewAction
from app.models.user import User
from app.schemas.campaign_asset import CampaignAssetRead
from app.schemas.content_template import ContentTemplateRead
from app.services.access import assert_helper_tool_plan_access
from app.services.assets import list_campaign_assets
from app.services.campaigns import get_campaign
from app.services.drafts import get_draft
from app.services.reviews import get_draft_review_thread
from app.services.templates import list_templates
from app.tools.advanced_schemas import (
    AdvancedToolExecution,
    AdvancedToolContext,
    AssetRecommendationItem,
    AssetRecommendationRequest,
    AssetRecommendationResponse,
    BrandVoiceValidatorRequest,
    BrandVoiceValidatorResponse,
    CrossChannelAdaptationRequest,
    CrossChannelAdaptationResponse,
    LLMBrandVoiceValidatorOutput,
    LLMCrossChannelAdaptationOutput,
    LLMReviewFeedbackChecklistOutput,
    RevisionChecklistItem,
    ReviewFeedbackToRevisionChecklistRequest,
    ReviewFeedbackToRevisionChecklistResponse,
    TemplateRecommendationItem,
    TemplateRecommendationRequest,
    TemplateRecommendationResponse,
)
from app.tools.llm import LLMProviderError, LLMProviderNotConfiguredError, get_llm_provider
from app.tools.schemas import ValidationCheckResult
from app.tools.services import fetch_brand_guidelines

STOPWORDS = {
    "about",
    "after",
    "against",
    "also",
    "because",
    "before",
    "between",
    "brand",
    "campaign",
    "channel",
    "content",
    "could",
    "draft",
    "from",
    "have",
    "into",
    "just",
    "more",
    "platform",
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

PLATFORM_RULES: dict[str, dict[str, object]] = {
    "linkedin": {
        "title_limit": 110,
        "recommended_content_type": "Thought leadership post",
        "notes": [
            "Lead with a business outcome or proof point.",
            "Keep the structure scannable for professionals.",
            "Close with a question or next-step CTA.",
        ],
        "default_cta": "What would you test next?",
        "hashtag_count": 3,
    },
    "instagram": {
        "title_limit": 80,
        "recommended_content_type": "Caption",
        "notes": [
            "Start with a hook that feels visual and immediate.",
            "Keep the copy concise and audience-facing.",
            "Use a clear prompt for engagement or save/share behavior.",
        ],
        "default_cta": "Save this for your next campaign sprint.",
        "hashtag_count": 5,
    },
    "email": {
        "title_limit": 65,
        "recommended_content_type": "Email",
        "notes": [
            "Use the title as a subject-line style opener.",
            "Make the value proposition explicit in the first paragraph.",
            "End with a single action and timing cue.",
        ],
        "default_cta": "Reply if you want the full plan.",
        "hashtag_count": 0,
    },
    "article": {
        "title_limit": 90,
        "recommended_content_type": "Article",
        "notes": [
            "Frame the title around the main thesis.",
            "Expand the body into a stronger editorial narrative.",
            "Finish with a practical takeaway rather than a hard sell.",
        ],
        "default_cta": "Use this as the next section or takeaway.",
        "hashtag_count": 0,
    },
}

PLATFORM_ASSET_TYPES: dict[str, set[str]] = {
    "linkedin": {"carousel", "deck", "graphic", "image", "pdf"},
    "instagram": {"graphic", "image", "photo", "reel", "story", "video"},
    "email": {"attachment", "banner", "graphic", "image", "pdf"},
    "article": {"diagram", "graphic", "image", "infographic", "reference"},
}

ACTION_PREFIX_PATTERN = re.compile(r"^(please|can you|could you|let's|make sure to|need to)\s+", flags=re.IGNORECASE)


@dataclass(slots=True)
class ResolvedDraftContext:
    draft_id: int | None
    brand_id: int
    brand_name: str
    campaign_id: int | None
    campaign_name: str | None
    title: str | None
    platform: str | None
    content_type: str | None
    content_body: str | None
    preferred_channels: list[str]
    tone_of_voice: str | None
    target_audience: str | None
    guidelines_summary: str | None

    def to_schema(self) -> AdvancedToolContext:
        return AdvancedToolContext(
            draft_id=self.draft_id,
            brand_id=self.brand_id,
            brand_name=self.brand_name,
            campaign_id=self.campaign_id,
            campaign_name=self.campaign_name,
            title=self.title,
            platform=self.platform,
            content_type=self.content_type,
        )


@dataclass(slots=True)
class StructuredLLMAttempt:
    payload: BaseModel | None
    execution: AdvancedToolExecution


def _normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _excerpt(value: str | None, *, limit: int = 180) -> str:
    normalized = _normalize_text(value)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3].rstrip()}..."


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


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _normalize_text(value).lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(_normalize_text(value))
    return deduped


def _platform_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _split_sentences(value: str | None) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", normalized) if segment.strip()]


def _clip(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3].rstrip()}..."


def _execution_metadata(
    mode: str,
    *,
    provider_name: str | None = None,
    model: str | None = None,
    fallback_reason: str | None = None,
) -> AdvancedToolExecution:
    return AdvancedToolExecution(
        mode=mode,
        provider_name=provider_name,
        model=model,
        fallback_reason=fallback_reason,
    )


def _build_llm_input(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)


def _attempt_llm_structured_output(
    *,
    schema_name: str,
    schema_model: type[BaseModel],
    instructions: str,
    input_payload: dict[str, Any],
) -> StructuredLLMAttempt:
    try:
        provider = get_llm_provider()
    except LLMProviderNotConfiguredError:
        return StructuredLLMAttempt(payload=None, execution=_execution_metadata("deterministic"))

    result = None
    try:
        result = provider.generate_structured_output(
            schema_name=schema_name,
            schema_model=schema_model,
            instructions=instructions,
            input_text=_build_llm_input(input_payload),
        )
        payload = schema_model.model_validate(result.payload)
    except (LLMProviderError, ValidationError) as exc:
        return StructuredLLMAttempt(
            payload=None,
            execution=_execution_metadata(
                "deterministic_fallback",
                provider_name=result.provider_name if result is not None else provider.provider_name,
                model=result.model if result is not None else None,
                fallback_reason=_excerpt(str(exc), limit=240),
            ),
        )

    return StructuredLLMAttempt(
        payload=payload,
        execution=_execution_metadata("llm", provider_name=result.provider_name, model=result.model),
    )


def _resolve_context(
    db: Session,
    *,
    user: User,
    tool_name: str,
    draft_id: int | None,
    brand_id: int | None,
    campaign_id: int | None,
    title: str | None,
    platform: str | None,
    content_type: str | None,
    content_body: str | None,
    require_body: bool = False,
    require_campaign: bool = False,
) -> ResolvedDraftContext:
    draft = get_draft(db, draft_id=draft_id, user=user) if draft_id is not None else None
    campaign = None

    if draft is not None:
        if brand_id is not None and brand_id != draft.brand_id:
            raise ValueError("brand_id must match the draft's brand.")
        if campaign_id is not None and campaign_id != draft.campaign_id:
            raise ValueError("campaign_id must match the draft's campaign.")
        brand_id = draft.brand_id
        campaign_id = draft.campaign_id
        title = title or draft.title
        platform = platform or draft.platform
        content_type = content_type or draft.content_type
        content_body = content_body if content_body is not None else draft.content_body

    if campaign_id is not None and draft is None:
        campaign = get_campaign(db, campaign_id=campaign_id, user=user)
        if brand_id is not None and brand_id != campaign.brand_id:
            raise ValueError("campaign_id must belong to the supplied brand_id.")
        brand_id = campaign.brand_id

    if brand_id is None:
        raise ValueError("brand_id is required when draft_id is not provided.")

    if require_campaign and campaign_id is None:
        raise ValueError("campaign_id is required when draft_id is not provided.")

    if require_body and not _normalize_text(content_body):
        raise ValueError("content_body is required when the draft does not contain body copy.")

    assert_helper_tool_plan_access(
        db,
        brand_id=brand_id,
        user_id=user.id,
        tool_name=tool_name,
    )
    brand = fetch_brand_guidelines(
        db,
        brand_id=brand_id,
        user=user,
        enforce_tool_access=False,
    )

    return ResolvedDraftContext(
        draft_id=draft.id if draft is not None else draft_id,
        brand_id=brand.brand_id,
        brand_name=brand.brand_name,
        campaign_id=campaign_id,
        campaign_name=(draft.campaign_name if draft is not None else campaign.name if campaign is not None else None),
        title=_normalize_text(title) or None,
        platform=_normalize_text(platform) or None,
        content_type=_normalize_text(content_type) or None,
        content_body=_normalize_text(content_body) or None,
        preferred_channels=brand.preferred_channels,
        tone_of_voice=brand.tone_of_voice,
        target_audience=brand.target_audience,
        guidelines_summary=brand.guidelines_summary,
    )


def _brand_voice_llm_instructions() -> str:
    return (
        "You are evaluating brand-voice alignment for a marketing draft. "
        "Return structured JSON only. Score the draft from 0 to 100. "
        "Use verdict 'pass' for strong alignment, 'warn' for partial alignment, and 'fail' for clearly off-brand copy. "
        "Use only these check names: content_depth, channel_alignment, voice_trait_coverage, audience_alignment, pacing_and_emphasis. "
        "Each check detail should be concrete, concise, and grounded in the provided draft and brand profile. "
        "Revision suggestions should be directly actionable and limited to the most important edits."
    )


def _cross_channel_llm_instructions() -> str:
    return (
        "You are adapting marketing copy from one channel to another. Return structured JSON only. "
        "Preserve the intent of the original draft, keep the output usable as real campaign copy, "
        "and follow the provided target-platform rules when possible. "
        "Warnings should call out channel-fit or missing-context issues only when they are material."
    )


def _review_feedback_llm_instructions(*, limit: int) -> str:
    return (
        "You are converting review comments into a revision checklist for a content draft. "
        "Return structured JSON only. "
        f"Produce no more than {limit} checklist items. "
        "Checklist items must be concrete, deduplicated, and phrased as actionable edits. "
        "Use 'high' priority for blocking or rejected feedback, 'medium' for normal revision work, and 'low' for polish. "
        "Preserved strengths should capture positive feedback worth retaining in the next revision."
    )


def _brand_voice_llm_input(context: ResolvedDraftContext) -> dict[str, Any]:
    content_text = " ".join(part for part in [context.title, context.content_body] if part)
    return {
        "context": context.to_schema().model_dump(mode="json"),
        "brand_profile": {
            "tone_of_voice": context.tone_of_voice,
            "target_audience": context.target_audience,
            "preferred_channels": context.preferred_channels,
            "guidelines_summary": context.guidelines_summary,
        },
        "draft": {
            "title": context.title,
            "platform": context.platform,
            "content_type": context.content_type,
            "content_body": context.content_body,
            "word_count": len((context.content_body or "").split()),
            "keywords": _extract_keywords(content_text, limit=24),
        },
    }


def _cross_channel_llm_input(
    *,
    context: ResolvedDraftContext,
    payload: CrossChannelAdaptationRequest,
    source_platform: str,
    target_platform: str,
) -> dict[str, Any]:
    target_key = _platform_key(target_platform)
    rules = PLATFORM_RULES.get(target_key, {})
    return {
        "context": context.to_schema().model_dump(mode="json"),
        "brand_profile": {
            "preferred_channels": context.preferred_channels,
            "tone_of_voice": context.tone_of_voice,
            "target_audience": context.target_audience,
            "guidelines_summary": context.guidelines_summary,
        },
        "source_platform": source_platform,
        "target_platform": target_platform,
        "options": {
            "preserve_call_to_action": payload.preserve_call_to_action,
            "include_hashtags": payload.include_hashtags,
        },
        "platform_rules": rules,
        "draft": {
            "title": context.title,
            "content_type": context.content_type,
            "content_body": context.content_body,
        },
    }


def _review_feedback_llm_input(
    *,
    context: ResolvedDraftContext,
    review_comments: list[dict[str, Any]],
    limit: int,
) -> dict[str, Any]:
    return {
        "context": context.to_schema().model_dump(mode="json"),
        "brand_profile": {
            "tone_of_voice": context.tone_of_voice,
            "target_audience": context.target_audience,
            "guidelines_summary": context.guidelines_summary,
        },
        "limit": limit,
        "review_comments": review_comments,
    }


def brand_voice_validator(
    db: Session,
    *,
    payload: BrandVoiceValidatorRequest,
    user: User,
) -> BrandVoiceValidatorResponse:
    context = _resolve_context(
        db,
        user=user,
        tool_name="brand_voice_validator",
        draft_id=payload.draft_id,
        brand_id=payload.brand_id,
        campaign_id=payload.campaign_id,
        title=payload.title,
        platform=payload.platform,
        content_type=payload.content_type,
        content_body=payload.content_body,
        require_body=True,
    )

    llm_attempt = _attempt_llm_structured_output(
        schema_name="brand_voice_validation",
        schema_model=LLMBrandVoiceValidatorOutput,
        instructions=_brand_voice_llm_instructions(),
        input_payload=_brand_voice_llm_input(context),
    )
    if isinstance(llm_attempt.payload, LLMBrandVoiceValidatorOutput):
        return BrandVoiceValidatorResponse(
            context=context.to_schema(),
            execution=llm_attempt.execution,
            **llm_attempt.payload.model_dump(mode="json"),
        )

    deterministic = _brand_voice_validator_deterministic(context)
    if llm_attempt.execution.mode == "deterministic":
        return deterministic
    return deterministic.model_copy(update={"execution": llm_attempt.execution})


def _brand_voice_validator_deterministic(context: ResolvedDraftContext) -> BrandVoiceValidatorResponse:
    execution = _execution_metadata("deterministic")

    content_text = " ".join(part for part in [context.title, context.content_body] if part)
    content_keywords = set(_extract_keywords(content_text, limit=40))
    voice_traits = _extract_keywords(context.tone_of_voice, context.guidelines_summary, limit=14)
    audience_terms = _extract_keywords(context.target_audience, limit=10)
    aligned_traits = [trait for trait in voice_traits if trait in content_keywords]
    missing_traits = [trait for trait in voice_traits if trait not in content_keywords]
    exclamation_count = (context.content_body or "").count("!")
    uppercase_tokens = re.findall(r"\b[A-Z]{4,}\b", context.content_body or "")

    checks: list[ValidationCheckResult] = []
    score = 100

    word_count = len((context.content_body or "").split())
    if word_count < 24:
        score -= 15
        checks.append(
            ValidationCheckResult(
                check="content_depth",
                status="warn",
                detail="The draft is brief, which makes it harder to express the brand voice consistently.",
            )
        )
    else:
        checks.append(
            ValidationCheckResult(
                check="content_depth",
                status="pass",
                detail="The draft has enough body copy to evaluate tone and voice with useful signal.",
            )
        )

    if context.platform and context.preferred_channels:
        preferred_channel_keys = {_platform_key(channel) for channel in context.preferred_channels}
        if _platform_key(context.platform) in preferred_channel_keys:
            checks.append(
                ValidationCheckResult(
                    check="channel_alignment",
                    status="pass",
                    detail=f"{context.platform} appears in the brand's preferred channel list.",
                )
            )
        else:
            score -= 15
            checks.append(
                ValidationCheckResult(
                    check="channel_alignment",
                    status="warn",
                    detail=(
                        f"{context.platform} is not in the stored preferred channels: "
                        f"{', '.join(context.preferred_channels)}."
                    ),
                )
            )
    else:
        checks.append(
            ValidationCheckResult(
                check="channel_alignment",
                status="warn",
                detail="Platform or preferred-channel context is missing, so channel alignment could not be confirmed.",
            )
        )

    if voice_traits:
        if len(aligned_traits) >= max(1, min(3, len(voice_traits) // 3 or 1)):
            checks.append(
                ValidationCheckResult(
                    check="voice_trait_coverage",
                    status="pass",
                    detail=f"The draft reflects brand voice traits such as {', '.join(aligned_traits[:4])}.",
                )
            )
        else:
            score -= 25
            checks.append(
                ValidationCheckResult(
                    check="voice_trait_coverage",
                    status="fail" if not aligned_traits else "warn",
                    detail=(
                        "The copy is not strongly anchored in the stored brand voice. "
                        f"Missing signals include {', '.join(missing_traits[:4]) or 'tone markers'}."
                    ),
                )
            )
    else:
        checks.append(
            ValidationCheckResult(
                check="voice_trait_coverage",
                status="warn",
                detail="The brand profile does not include enough tone detail to perform a deeper voice-trait match.",
            )
        )

    if audience_terms:
        audience_matches = [term for term in audience_terms if term in content_keywords]
        if audience_matches:
            checks.append(
                ValidationCheckResult(
                    check="audience_alignment",
                    status="pass",
                    detail=f"The draft references audience cues such as {', '.join(audience_matches[:4])}.",
                )
            )
        else:
            score -= 10
            checks.append(
                ValidationCheckResult(
                    check="audience_alignment",
                    status="warn",
                    detail="The draft does not clearly echo the stored target audience language.",
                )
            )
    else:
        checks.append(
            ValidationCheckResult(
                check="audience_alignment",
                status="warn",
                detail="No target-audience profile was stored for this brand.",
            )
        )

    if exclamation_count > 3 or len(uppercase_tokens) > 2:
        score -= 10
        checks.append(
            ValidationCheckResult(
                check="pacing_and_emphasis",
                status="warn",
                detail="The copy uses heavy emphasis, which risks sounding more aggressive than the stored brand voice.",
            )
        )
    else:
        checks.append(
            ValidationCheckResult(
                check="pacing_and_emphasis",
                status="pass",
                detail="The punctuation and emphasis level stay within a controlled editorial tone.",
            )
        )

    suggestions: list[str] = []
    if missing_traits:
        suggestions.append(f"Work brand language such as {', '.join(missing_traits[:3])} into the lead and CTA.")
    if audience_terms and not any(term in content_keywords for term in audience_terms):
        suggestions.append("Name the audience problem or outcome more explicitly so the copy feels tailored.")
    if exclamation_count > 3 or len(uppercase_tokens) > 2:
        suggestions.append("Reduce all-caps or exclamation-heavy phrasing to keep the tone more controlled.")
    if word_count < 24:
        suggestions.append("Add one more proof point, benefit, or CTA detail so the tone has enough room to land.")
    if context.platform and context.preferred_channels and _platform_key(context.platform) not in {
        _platform_key(channel) for channel in context.preferred_channels
    }:
        suggestions.append(
            f"Consider adapting the draft for one of the preferred channels: {', '.join(context.preferred_channels[:3])}."
        )

    score = max(score, 0)
    if score >= 80 and not any(check.status == "fail" for check in checks):
        verdict = "pass"
    elif score >= 60:
        verdict = "warn"
    else:
        verdict = "fail"

    return BrandVoiceValidatorResponse(
        context=context.to_schema(),
        execution=execution,
        score=score,
        verdict=verdict,
        summary=(
            f"Brand voice validation returned {verdict} at {score}/100 with "
            f"{len(aligned_traits)} aligned traits and {len(suggestions)} recommended edits."
        ),
        aligned_traits=aligned_traits,
        missing_traits=missing_traits,
        checks=checks,
        revision_suggestions=suggestions,
    )


def cross_channel_adaptation(
    db: Session,
    *,
    payload: CrossChannelAdaptationRequest,
    user: User,
) -> CrossChannelAdaptationResponse:
    context = _resolve_context(
        db,
        user=user,
        tool_name="cross_channel_adaptation",
        draft_id=payload.draft_id,
        brand_id=payload.brand_id,
        campaign_id=payload.campaign_id,
        title=payload.title,
        platform=payload.platform,
        content_type=payload.content_type,
        content_body=payload.content_body,
        require_body=True,
    )
    source_platform = _normalize_text(payload.source_platform) or context.platform or "Generic"
    target_platform = _normalize_text(payload.target_platform)

    llm_attempt = _attempt_llm_structured_output(
        schema_name="cross_channel_adaptation",
        schema_model=LLMCrossChannelAdaptationOutput,
        instructions=_cross_channel_llm_instructions(),
        input_payload=_cross_channel_llm_input(
            context=context,
            payload=payload,
            source_platform=source_platform,
            target_platform=target_platform,
        ),
    )
    if isinstance(llm_attempt.payload, LLMCrossChannelAdaptationOutput):
        return CrossChannelAdaptationResponse(
            context=context.to_schema(),
            execution=llm_attempt.execution,
            source_platform=source_platform,
            target_platform=target_platform,
            **llm_attempt.payload.model_dump(mode="json"),
        )

    deterministic = _cross_channel_adaptation_deterministic(
        context=context,
        payload=payload,
        source_platform=source_platform,
        target_platform=target_platform,
    )
    if llm_attempt.execution.mode == "deterministic":
        return deterministic
    return deterministic.model_copy(update={"execution": llm_attempt.execution})


def _cross_channel_adaptation_deterministic(
    *,
    context: ResolvedDraftContext,
    payload: CrossChannelAdaptationRequest,
    source_platform: str,
    target_platform: str,
) -> CrossChannelAdaptationResponse:
    execution = _execution_metadata("deterministic")
    rules = PLATFORM_RULES.get(_platform_key(target_platform), {})
    title_limit = int(rules.get("title_limit", 90))
    sentences = _split_sentences(context.content_body)
    lead_sentence = sentences[0] if sentences else context.content_body or ""
    support_sentences = sentences[1:4] if len(sentences) > 1 else []
    base_title = context.title or lead_sentence

    cta = None
    if payload.preserve_call_to_action and sentences:
        for sentence in reversed(sentences):
            lowered = sentence.lower()
            if "?" in sentence or any(verb in lowered for verb in ("reply", "join", "learn", "download", "explore", "book", "save", "share")):
                cta = sentence
                break
    cta = cta or str(rules.get("default_cta", "Take the next step."))

    target_key = _platform_key(target_platform)
    hashtags = _derive_hashtags(context=context, limit=int(rules.get("hashtag_count", 0))) if payload.include_hashtags else []
    adaptation_notes = [str(note) for note in rules.get("notes", [])]
    warnings: list[str] = []

    if target_key == "linkedin":
        adapted_title = _clip(base_title, limit=title_limit)
        body_parts = [_clip(lead_sentence, limit=220)]
        if support_sentences:
            body_parts.append(" ".join(_clip(sentence, limit=220) for sentence in support_sentences[:2]))
        body_parts.append(cta)
        adapted_body = "\n\n".join(part for part in body_parts if part)
    elif target_key == "instagram":
        adapted_title = _clip(base_title, limit=title_limit)
        body_parts = [_clip(lead_sentence, limit=160)]
        if support_sentences:
            body_parts.append(" ".join(_clip(sentence, limit=140) for sentence in support_sentences[:1]))
        body_parts.append(cta)
        if hashtags:
            body_parts.append(" ".join(hashtags))
        adapted_body = "\n\n".join(part for part in body_parts if part)
    elif target_key == "email":
        adapted_title = _clip(base_title, limit=title_limit)
        body_parts = [
            _clip(lead_sentence, limit=220),
            " ".join(support_sentences[:2]) or "Here is the core message, framed for a direct inbox read.",
            cta,
        ]
        adapted_body = "\n\n".join(part for part in body_parts if part)
    elif target_key == "article":
        adapted_title = _clip(base_title, limit=title_limit)
        body_parts = [
            _clip(lead_sentence, limit=260),
            " ".join(support_sentences[:3]) or "Expand the supporting detail with proof points, examples, or campaign context.",
            cta,
        ]
        adapted_body = "\n\n".join(part for part in body_parts if part)
    else:
        adapted_title = _clip(base_title, limit=title_limit)
        adapted_body = "\n\n".join(part for part in [lead_sentence, " ".join(support_sentences[:2]), cta] if part)
        warnings.append(f"No specialized adaptation template was defined for {target_platform}.")

    if context.preferred_channels and target_key not in {_platform_key(channel) for channel in context.preferred_channels}:
        warnings.append(
            f"{target_platform} is not listed in the preferred channels for {context.brand_name}."
        )

    return CrossChannelAdaptationResponse(
        context=context.to_schema(),
        execution=execution,
        source_platform=source_platform,
        target_platform=target_platform,
        adapted_title=adapted_title or None,
        adapted_body=adapted_body,
        recommended_content_type=str(rules.get("recommended_content_type")) if rules else context.content_type,
        adaptation_notes=adaptation_notes,
        warnings=warnings,
        derived_hashtags=hashtags,
    )


def _derive_hashtags(*, context: ResolvedDraftContext, limit: int) -> list[str]:
    if limit <= 0:
        return []

    raw_keywords = _extract_keywords(
        context.brand_name,
        context.title,
        context.content_body,
        context.content_type,
        limit=limit + 3,
    )
    hashtags: list[str] = []
    for keyword in raw_keywords:
        tag = f"#{re.sub(r'[^a-z0-9]', '', keyword.title())}"
        if tag == "#" or tag in hashtags:
            continue
        hashtags.append(tag)
        if len(hashtags) >= limit:
            break
    return hashtags


def template_recommendation(
    db: Session,
    *,
    payload: TemplateRecommendationRequest,
    user: User,
) -> TemplateRecommendationResponse:
    context = _resolve_context(
        db,
        user=user,
        tool_name="template_recommendation",
        draft_id=payload.draft_id,
        brand_id=payload.brand_id,
        campaign_id=payload.campaign_id,
        title=payload.title,
        platform=payload.platform,
        content_type=payload.content_type,
        content_body=payload.content_body,
    )
    templates = list_templates(db, user=user, brand_id=context.brand_id)
    content_keywords = set(_extract_keywords(context.title, context.content_body, context.content_type, limit=40))

    scored: list[tuple[int, ContentTemplateRead, list[str]]] = []
    for template in templates:
        score = 15
        reasons: list[str] = ["Brand-owned template available for reuse."]

        if context.platform and template.platform and _platform_key(template.platform) == _platform_key(context.platform):
            score += 25
            reasons.append(f"Platform matches {context.platform}.")
        elif context.platform and template.platform is None:
            score += 8
            reasons.append("Template is platform-flexible.")

        if context.content_type and template.content_type and template.content_type.lower() == context.content_type.lower():
            score += 20
            reasons.append(f"Content type matches {context.content_type}.")

        template_keywords = set(_extract_keywords(template.name, template.description, template.body, limit=28))
        overlap = [keyword for keyword in template_keywords if keyword in content_keywords]
        if overlap:
            score += min(30, len(overlap) * 6)
            reasons.append(f"Shared vocabulary: {', '.join(overlap[:4])}.")

        if context.title and context.title.lower() in (template.description or "").lower():
            score += 5
            reasons.append("Description references the current draft topic directly.")

        scored.append((min(score, 100), template, reasons))

    scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    selected = scored[: payload.limit]

    return TemplateRecommendationResponse(
        context=context.to_schema(),
        execution=_execution_metadata("deterministic"),
        total_candidates=len(scored),
        recommendations=[
            TemplateRecommendationItem(
                id=template.id,
                name=template.name,
                description=template.description,
                template_type=template.template_type,
                platform=template.platform,
                content_type=template.content_type,
                score=score,
                reasons=reasons,
                excerpt=_excerpt(template.body),
                updated_at=template.updated_at,
            )
            for score, template, reasons in selected
        ],
    )


def asset_recommendation(
    db: Session,
    *,
    payload: AssetRecommendationRequest,
    user: User,
) -> AssetRecommendationResponse:
    context = _resolve_context(
        db,
        user=user,
        tool_name="asset_recommendation",
        draft_id=payload.draft_id,
        brand_id=payload.brand_id,
        campaign_id=payload.campaign_id,
        title=payload.title,
        platform=payload.platform,
        content_type=payload.content_type,
        content_body=payload.content_body,
        require_campaign=True,
    )
    assets = list_campaign_assets(db, campaign_id=context.campaign_id, user=user)
    content_keywords = set(_extract_keywords(context.title, context.content_body, context.content_type, limit=40))
    preferred_asset_types = PLATFORM_ASSET_TYPES.get(_platform_key(context.platform), set())

    scored: list[tuple[int, CampaignAssetRead, list[str]]] = []
    for asset in assets:
        score = 10
        reasons: list[str] = ["Campaign asset is available in the active workspace."]
        asset_type_key = _platform_key(asset.asset_type)

        if asset_type_key in {_platform_key(value) for value in preferred_asset_types}:
            score += 25
            reasons.append(f"Asset type fits {context.platform or 'the draft platform'} delivery.")

        asset_keywords = set(_extract_keywords(asset.name, asset.notes, asset.mime_type, limit=24))
        overlap = [keyword for keyword in asset_keywords if keyword in content_keywords]
        if overlap:
            score += min(30, len(overlap) * 7)
            reasons.append(f"Keyword overlap with the draft: {', '.join(overlap[:4])}.")

        if context.content_type and context.content_type.lower() in f"{asset.name} {asset.notes or ''}".lower():
            score += 10
            reasons.append(f"Notes reference the {context.content_type} format.")

        if context.platform and context.platform.lower() in f"{asset.name} {asset.notes or ''}".lower():
            score += 10
            reasons.append(f"Notes reference {context.platform}.")

        scored.append((min(score, 100), asset, reasons))

    scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    selected = scored[: payload.limit]

    return AssetRecommendationResponse(
        context=context.to_schema(),
        execution=_execution_metadata("deterministic"),
        total_candidates=len(scored),
        recommendations=[
            AssetRecommendationItem(
                id=asset.id,
                name=asset.name,
                asset_type=asset.asset_type,
                file_url=asset.file_url,
                thumbnail_url=asset.thumbnail_url,
                mime_type=asset.mime_type,
                file_size_bytes=asset.file_size_bytes,
                notes=asset.notes,
                updated_at=asset.updated_at,
                score=score,
                reasons=reasons,
            )
            for score, asset, reasons in selected
        ],
    )


def review_feedback_to_revision_checklist(
    db: Session,
    *,
    payload: ReviewFeedbackToRevisionChecklistRequest,
    user: User,
) -> ReviewFeedbackToRevisionChecklistResponse:
    context = _resolve_context(
        db,
        user=user,
        tool_name="review_feedback_to_revision_checklist",
        draft_id=payload.draft_id,
        brand_id=None,
        campaign_id=None,
        title=None,
        platform=None,
        content_type=None,
        content_body=None,
    )
    review_thread = get_draft_review_thread(db, draft_id=payload.draft_id, user=user)
    commented_reviews = [review for review in review_thread.reviews if review.comment]
    llm_attempt = _attempt_llm_structured_output(
        schema_name="review_feedback_revision_checklist",
        schema_model=LLMReviewFeedbackChecklistOutput,
        instructions=_review_feedback_llm_instructions(limit=payload.limit),
        input_payload=_review_feedback_llm_input(
            context=context,
            limit=payload.limit,
            review_comments=[
                {
                    "action": review.action,
                    "comment": _normalize_text(review.comment),
                    "created_at": review.created_at,
                }
                for review in commented_reviews
                if _normalize_text(review.comment)
            ],
        ),
    )
    if isinstance(llm_attempt.payload, LLMReviewFeedbackChecklistOutput):
        return ReviewFeedbackToRevisionChecklistResponse(
            context=context.to_schema(),
            execution=llm_attempt.execution,
            summary=llm_attempt.payload.summary,
            checklist_items=llm_attempt.payload.checklist_items[: payload.limit],
            preserved_strengths=_dedupe_preserve_order(llm_attempt.payload.preserved_strengths)[:5],
            source_comment_count=len(commented_reviews),
            blocker_count=sum(1 for review in commented_reviews if review.action == DraftReviewAction.rejected),
        )

    deterministic = _review_feedback_to_revision_checklist_deterministic(
        context=context,
        payload=payload,
        commented_reviews=commented_reviews,
    )
    if llm_attempt.execution.mode == "deterministic":
        return deterministic
    return deterministic.model_copy(update={"execution": llm_attempt.execution})


def _review_feedback_to_revision_checklist_deterministic(
    *,
    context: ResolvedDraftContext,
    payload: ReviewFeedbackToRevisionChecklistRequest,
    commented_reviews: list[Any],
) -> ReviewFeedbackToRevisionChecklistResponse:
    execution = _execution_metadata("deterministic")
    checklist_items: list[RevisionChecklistItem] = []
    preserved_strengths: list[str] = []
    seen_items: set[str] = set()

    for review in commented_reviews:
        comment_text = _normalize_text(review.comment)
        if not comment_text:
            continue

        if review.action == DraftReviewAction.approved:
            preserved_strengths.append(_excerpt(comment_text, limit=160))
            continue

        for segment in _feedback_segments(comment_text):
            action_item = _feedback_to_action_item(segment)
            normalized_item = action_item.lower()
            if normalized_item in seen_items:
                continue
            seen_items.add(normalized_item)
            checklist_items.append(
                RevisionChecklistItem(
                    item=action_item,
                    priority=_priority_for_action(review.action),
                    source_action=review.action,
                    source_excerpt=_excerpt(segment, limit=140),
                    guidance=_guidance_for_feedback(segment),
                )
            )
            if len(checklist_items) >= payload.limit:
                break
        if len(checklist_items) >= payload.limit:
            break

    if not checklist_items:
        fallback_excerpt = _excerpt(commented_reviews[0].comment, limit=140) if commented_reviews else "No written review comments found."
        checklist_items.append(
            RevisionChecklistItem(
                item="Confirm the next revision focus before resubmitting.",
                priority="medium",
                source_action=commented_reviews[0].action if commented_reviews else DraftReviewAction.commented,
                source_excerpt=fallback_excerpt,
                guidance="Use the review thread to capture concrete changes so the next cycle is traceable.",
            )
        )

    return ReviewFeedbackToRevisionChecklistResponse(
        context=context.to_schema(),
        execution=execution,
        summary=(
            f"Converted {len(commented_reviews)} review comments into "
            f"{len(checklist_items)} revision checklist items."
        ),
        checklist_items=checklist_items,
        preserved_strengths=_dedupe_preserve_order(preserved_strengths)[:5],
        source_comment_count=len(commented_reviews),
        blocker_count=sum(1 for review in commented_reviews if review.action == DraftReviewAction.rejected),
    )


def _feedback_segments(comment: str) -> list[str]:
    segments = re.split(r"(?:\n+|(?<=[.!?])\s+)", comment)
    filtered = []
    for segment in segments:
        normalized = _normalize_text(segment)
        if len(normalized) < 8:
            continue
        if normalized.lower() in {"looks good", "thanks", "approved", "great work"}:
            continue
        filtered.append(normalized)
    return filtered


def _feedback_to_action_item(segment: str) -> str:
    cleaned = ACTION_PREFIX_PATTERN.sub("", segment).rstrip(".")
    if re.match(r"^(add|clarify|tighten|remove|rewrite|expand|shorten|show|include|swap|connect|update)\b", cleaned, flags=re.IGNORECASE):
        return cleaned[:1].upper() + cleaned[1:]
    return f"Address feedback: {cleaned}"


def _priority_for_action(action: DraftReviewAction) -> str:
    if action == DraftReviewAction.rejected:
        return "high"
    if action == DraftReviewAction.resubmitted:
        return "low"
    return "medium"


def _guidance_for_feedback(segment: str) -> str:
    lowered = segment.lower()
    if "tone" in lowered or "voice" in lowered or "brand" in lowered:
        return "Mirror the stored brand voice and remove phrasing that feels off-brand."
    if "cta" in lowered or "call to action" in lowered or "next step" in lowered:
        return "Make the next action explicit and easy for the audience to follow."
    if any(keyword in lowered for keyword in ("proof", "data", "example", "evidence")):
        return "Add concrete proof, examples, or specifics to support the claim."
    if any(keyword in lowered for keyword in ("short", "tight", "trim", "concise")):
        return "Tighten the copy and front-load the most important message."
    if any(keyword in lowered for keyword in ("visual", "asset", "image", "graphic")):
        return "Pair the copy update with a supporting campaign asset or visual cue."
    return "Update the draft and resubmit with a clear note explaining what changed."
