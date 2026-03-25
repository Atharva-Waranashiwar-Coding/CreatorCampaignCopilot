from __future__ import annotations

import importlib.util

from app.core.config import settings
from app.tools.schemas import HelperToolCatalogItem, HelperToolCatalogResponse


def _mcp_runtime_available() -> bool:
    return importlib.util.find_spec("fastapi_mcp") is not None


def get_helper_tool_catalog() -> HelperToolCatalogResponse:
    mcp_available = _mcp_runtime_available()
    mcp_exposed = settings.mcp_helpers_enabled and mcp_available and (
        settings.mcp_enable_http_transport or settings.mcp_enable_sse_transport
    )

    tools = [
        HelperToolCatalogItem(
            name="fetch_brand_guidelines",
            mcp_tool_name="fetch_brand_guidelines",
            description="Return stored brand voice, audience, channel preferences, and guideline context for a brand.",
            rest_path=f"{settings.api_prefix}/tools/helpers/fetch-brand-guidelines",
            http_method="POST",
            target_entity_type="brand",
            service_bindings=[
                "app.services.brands.get_brand",
            ],
            mcp_exposed=mcp_exposed,
        ),
        HelperToolCatalogItem(
            name="fetch_templates",
            mcp_tool_name="fetch_templates",
            description="Return accessible content templates filtered by brand, platform, content type, and search terms.",
            rest_path=f"{settings.api_prefix}/tools/helpers/fetch-templates",
            http_method="POST",
            target_entity_type="brand",
            service_bindings=[
                "app.services.templates.list_templates",
            ],
            mcp_exposed=mcp_exposed,
        ),
        HelperToolCatalogItem(
            name="validate_content_against_guidelines",
            mcp_tool_name="validate_content_against_guidelines",
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
        HelperToolCatalogItem(
            name="retrieve_campaign_assets",
            mcp_tool_name="retrieve_campaign_assets",
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
        HelperToolCatalogItem(
            name="summarize_review_feedback",
            mcp_tool_name="summarize_review_feedback",
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
    ]

    return HelperToolCatalogResponse(
        mcp_helpers_enabled=settings.mcp_helpers_enabled,
        mcp_runtime_available=mcp_available,
        mcp_http_transport_enabled=settings.mcp_enable_http_transport,
        mcp_sse_transport_enabled=settings.mcp_enable_sse_transport,
        mcp_mount_path=settings.mcp_mount_path if mcp_exposed else None,
        tools=tools,
    )
