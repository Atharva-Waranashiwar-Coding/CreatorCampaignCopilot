from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.core.enums import DraftReviewAction
from app.models.tool_usage_log import ToolUsageLog
from app.tools.advanced_schemas import CrossChannelAdaptationRequest, ReviewFeedbackToRevisionChecklistRequest
from app.tools.advanced_services import (
    ResolvedDraftContext,
    _brand_voice_validator_deterministic,
    _cross_channel_adaptation_deterministic,
    _review_feedback_to_revision_checklist_deterministic,
)


def test_fetch_brand_guidelines_endpoint_returns_brand_context(client, seeded_workspace) -> None:
    response = client.post(
        "/api/tools/helpers/fetch-brand-guidelines",
        json={"brand_id": seeded_workspace.brand.id},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["brand_name"] == seeded_workspace.brand.name
    assert payload["current_user_role"] == "owner"
    assert "LinkedIn" in payload["preferred_channels"]
    assert payload["guidelines_summary"]


def test_brand_voice_validator_endpoint_blocks_when_advanced_helpers_are_locked(
    client,
    db_session,
    seeded_workspace,
) -> None:
    seeded_workspace.plan.features_json = {
        **seeded_workspace.plan.features_json,
        "advanced_ai_helpers": False,
    }
    db_session.add(seeded_workspace.plan)
    db_session.commit()

    response = client.post(
        "/api/tools/helpers/brand-voice-validator",
        json={
            "draft_id": seeded_workspace.draft.id,
            "brand_id": seeded_workspace.brand.id,
            "campaign_id": seeded_workspace.campaign.id,
            "title": seeded_workspace.draft.title,
            "platform": seeded_workspace.draft.platform,
            "content_type": seeded_workspace.draft.content_type,
            "content_body": seeded_workspace.draft.content_body,
        },
    )

    assert response.status_code == 403
    assert "advanced AI helpers" in response.json()["detail"]


def test_fetch_brand_guidelines_endpoint_returns_429_when_burst_limit_is_reached(
    client,
    db_session,
    seeded_workspace,
) -> None:
    seeded_workspace.plan.limits_json = {
        **seeded_workspace.plan.limits_json,
        "max_helper_runs_per_10_minutes": 1,
    }
    db_session.add(seeded_workspace.plan)
    db_session.add(
        ToolUsageLog(
            tool_name="fetch_brand_guidelines",
            actor_user_id=seeded_workspace.user.id,
            brand_id=seeded_workspace.brand.id,
            campaign_id=None,
            draft_id=None,
            target_entity_type="brand",
            target_entity_id=seeded_workspace.brand.id,
            invocation_source="rest",
            was_successful=True,
            request_payload={"brand_id": seeded_workspace.brand.id},
            result_summary={"brand_id": seeded_workspace.brand.id},
            request_trace={"brand_id": seeded_workspace.brand.id},
            result_trace={"brand_id": seeded_workspace.brand.id},
            created_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/tools/helpers/fetch-brand-guidelines",
        json={"brand_id": seeded_workspace.brand.id},
    )

    assert response.status_code == 429
    assert response.headers.get("retry-after")
    assert "burst limit" in response.json()["detail"]


def test_brand_voice_validator_deterministic_penalizes_off_brand_copy() -> None:
    context = ResolvedDraftContext(
        draft_id=1,
        brand_id=1,
        brand_name="Acme",
        campaign_id=1,
        campaign_name="Spring Launch",
        title="BUY NOW",
        platform="TikTok",
        content_type="Caption",
        content_body="BUY NOW!!! HUGE DROP!!! ACT FAST!!!",
        preferred_channels=["LinkedIn", "Instagram"],
        tone_of_voice="Measured, helpful, evidence-based",
        target_audience="Marketing leaders",
        guidelines_summary="Lead with outcomes and proof instead of hype.",
    )

    result = _brand_voice_validator_deterministic(context)

    assert result.verdict == "fail"
    assert result.score < 60
    assert result.missing_traits
    assert any("Reduce all-caps" in suggestion for suggestion in result.revision_suggestions)


def test_cross_channel_adaptation_deterministic_shapes_instagram_output() -> None:
    context = ResolvedDraftContext(
        draft_id=1,
        brand_id=1,
        brand_name="Acme",
        campaign_id=1,
        campaign_name="Spring Launch",
        title="Pipeline lessons from the launch sprint",
        platform="LinkedIn",
        content_type="Thought leadership post",
        content_body=(
            "Teams hit better launch windows when the proof points are planned early. "
            "It keeps review cycles shorter and CTA timing cleaner. "
            "Save this checklist for the next sprint."
        ),
        preferred_channels=["Instagram", "LinkedIn"],
        tone_of_voice="Measured, helpful, evidence-based",
        target_audience="Marketing leaders",
        guidelines_summary="Lead with outcomes and proof instead of hype.",
    )
    payload = CrossChannelAdaptationRequest(
        draft_id=1,
        brand_id=1,
        campaign_id=1,
        title=context.title,
        platform=context.platform,
        content_type=context.content_type,
        content_body=context.content_body,
        source_platform="LinkedIn",
        target_platform="Instagram",
        preserve_call_to_action=True,
        include_hashtags=True,
    )

    result = _cross_channel_adaptation_deterministic(
        context=context,
        payload=payload,
        source_platform="LinkedIn",
        target_platform="Instagram",
    )

    assert result.target_platform == "Instagram"
    assert result.recommended_content_type == "Caption"
    assert result.derived_hashtags
    assert "Save this checklist" in result.adapted_body


def test_revision_checklist_deterministic_prioritizes_rejected_feedback() -> None:
    context = ResolvedDraftContext(
        draft_id=1,
        brand_id=1,
        brand_name="Acme",
        campaign_id=1,
        campaign_name="Spring Launch",
        title="Proof-backed launch plan",
        platform="LinkedIn",
        content_type="Thought leadership post",
        content_body=None,
        preferred_channels=["LinkedIn"],
        tone_of_voice="Measured, helpful, evidence-based",
        target_audience="Marketing leaders",
        guidelines_summary="Lead with outcomes and proof instead of hype.",
    )
    payload = ReviewFeedbackToRevisionChecklistRequest(draft_id=1, limit=10)
    comments = [
        SimpleNamespace(
            action=DraftReviewAction.REJECTED,
            comment="Please tighten the CTA and add proof points before resubmitting.",
        ),
        SimpleNamespace(
            action=DraftReviewAction.APPROVED,
            comment="Strong opening and useful tone.",
        ),
    ]

    result = _review_feedback_to_revision_checklist_deterministic(
        context=context,
        payload=payload,
        commented_reviews=comments,
    )

    assert result.checklist_items
    assert result.checklist_items[0].priority == "high"
    assert any("proof" in item.guidance.lower() or "proof" in item.item.lower() for item in result.checklist_items)
    assert result.preserved_strengths == ["Strong opening and useful tone."]
