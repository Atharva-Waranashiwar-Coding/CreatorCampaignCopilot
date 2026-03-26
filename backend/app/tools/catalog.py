from __future__ import annotations

import importlib.util

from app.core.config import settings
from app.tools.definitions import get_helper_tool_definition
from app.tools.schemas import HelperToolCatalogItem, HelperToolCatalogResponse


def _mcp_runtime_available() -> bool:
    return importlib.util.find_spec("fastapi_mcp") is not None


def _catalog_item(
    *,
    name: str,
    description: str,
    rest_path: str,
    http_method: str,
    target_entity_type: str,
    service_bindings: list[str],
    mcp_exposed: bool,
) -> HelperToolCatalogItem:
    definition = get_helper_tool_definition(name)
    return HelperToolCatalogItem(
        name=name,
        mcp_tool_name=name,
        is_advanced=definition.is_advanced,
        required_feature_key=definition.required_feature_key,
        description=description,
        rest_path=rest_path,
        http_method=http_method,
        target_entity_type=target_entity_type,
        service_bindings=service_bindings,
        mcp_exposed=mcp_exposed,
    )


def get_helper_tool_catalog() -> HelperToolCatalogResponse:
    mcp_available = _mcp_runtime_available()
    mcp_exposed = settings.mcp_helpers_enabled and mcp_available and (
        settings.mcp_enable_http_transport or settings.mcp_enable_sse_transport
    )

    tools = [
        _catalog_item(
            name="fetch_brand_guidelines",
            description="Return stored brand voice, audience, channel preferences, and guideline context for a brand.",
            rest_path=f"{settings.api_prefix}/tools/helpers/fetch-brand-guidelines",
            http_method="POST",
            target_entity_type="brand",
            service_bindings=[
                "app.services.brands.get_brand",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="fetch_templates",
            description="Return accessible content templates filtered by brand, platform, content type, and search terms.",
            rest_path=f"{settings.api_prefix}/tools/helpers/fetch-templates",
            http_method="POST",
            target_entity_type="brand",
            service_bindings=[
                "app.services.templates.list_templates",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="validate_content_against_guidelines",
            description="Evaluate draft content against stored brand guidance and an optional template using deterministic checks.",
            rest_path=f"{settings.api_prefix}/tools/helpers/validate-content-against-guidelines",
            http_method="POST",
            target_entity_type="brand",
            service_bindings=[
                "app.tools.services.validate_content_against_guidelines",
                "app.services.brands.get_brand",
                "app.services.templates.get_template",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="retrieve_campaign_assets",
            description="Return asset references for an accessible campaign with optional asset-type or search filtering.",
            rest_path=f"{settings.api_prefix}/tools/helpers/retrieve-campaign-assets",
            http_method="POST",
            target_entity_type="campaign",
            service_bindings=[
                "app.services.campaigns.get_campaign",
                "app.services.assets.list_campaign_assets",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="summarize_review_feedback",
            description="Summarize draft review activity into blockers, approvals, recent comments, and action counts.",
            rest_path=f"{settings.api_prefix}/tools/helpers/summarize-review-feedback",
            http_method="POST",
            target_entity_type="content_draft",
            service_bindings=[
                "app.services.drafts.get_draft",
                "app.services.reviews.get_draft_review_thread",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="brand_voice_validator",
            description="Score draft tone against stored brand voice cues and return concrete revision suggestions.",
            rest_path=f"{settings.api_prefix}/tools/helpers/brand-voice-validator",
            http_method="POST",
            target_entity_type="content_draft",
            service_bindings=[
                "app.tools.advanced_services.brand_voice_validator",
                "app.services.drafts.get_draft",
                "app.services.brands.get_brand",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="cross_channel_adaptation",
            description="Adapt draft copy into another target channel while preserving the brand context and CTA intent.",
            rest_path=f"{settings.api_prefix}/tools/helpers/cross-channel-adaptation",
            http_method="POST",
            target_entity_type="content_draft",
            service_bindings=[
                "app.tools.advanced_services.cross_channel_adaptation",
                "app.services.drafts.get_draft",
                "app.services.brands.get_brand",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="template_recommendation",
            description="Rank brand templates against current draft context and explain why the strongest fits were chosen.",
            rest_path=f"{settings.api_prefix}/tools/helpers/template-recommendation",
            http_method="POST",
            target_entity_type="brand",
            service_bindings=[
                "app.tools.advanced_services.template_recommendation",
                "app.services.templates.list_templates",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="asset_recommendation",
            description="Rank campaign assets against the current draft context and platform needs.",
            rest_path=f"{settings.api_prefix}/tools/helpers/asset-recommendation",
            http_method="POST",
            target_entity_type="campaign",
            service_bindings=[
                "app.tools.advanced_services.asset_recommendation",
                "app.services.assets.list_campaign_assets",
                "app.services.campaigns.get_campaign",
            ],
            mcp_exposed=mcp_exposed,
        ),
        _catalog_item(
            name="review_feedback_to_revision_checklist",
            description="Convert review comments into a structured revision checklist with priority and guidance.",
            rest_path=f"{settings.api_prefix}/tools/helpers/review-feedback-to-revision-checklist",
            http_method="POST",
            target_entity_type="content_draft",
            service_bindings=[
                "app.tools.advanced_services.review_feedback_to_revision_checklist",
                "app.services.reviews.get_draft_review_thread",
                "app.services.drafts.get_draft",
            ],
            mcp_exposed=mcp_exposed,
        ),
    ]

    return HelperToolCatalogResponse(
        mcp_helpers_enabled=settings.mcp_helpers_enabled,
        mcp_runtime_available=mcp_available,
        mcp_http_transport_enabled=settings.mcp_enable_http_transport,
        mcp_sse_transport_enabled=settings.mcp_enable_sse_transport,
        mcp_mount_path=settings.mcp_mount_path if mcp_exposed else None,
        tools=tools,
    )
