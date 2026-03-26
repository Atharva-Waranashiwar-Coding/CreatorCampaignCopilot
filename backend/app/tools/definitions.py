from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HelperToolDefinition:
    name: str
    is_advanced: bool
    required_feature_key: str
    usage_metric_key: str


HELPER_TOOL_DEFINITIONS = {
    "fetch_brand_guidelines": HelperToolDefinition(
        name="fetch_brand_guidelines",
        is_advanced=False,
        required_feature_key="helper_tools",
        usage_metric_key="monthly_helper_runs",
    ),
    "fetch_templates": HelperToolDefinition(
        name="fetch_templates",
        is_advanced=False,
        required_feature_key="helper_tools",
        usage_metric_key="monthly_helper_runs",
    ),
    "validate_content_against_guidelines": HelperToolDefinition(
        name="validate_content_against_guidelines",
        is_advanced=False,
        required_feature_key="helper_tools",
        usage_metric_key="monthly_helper_runs",
    ),
    "retrieve_campaign_assets": HelperToolDefinition(
        name="retrieve_campaign_assets",
        is_advanced=False,
        required_feature_key="helper_tools",
        usage_metric_key="monthly_helper_runs",
    ),
    "summarize_review_feedback": HelperToolDefinition(
        name="summarize_review_feedback",
        is_advanced=False,
        required_feature_key="helper_tools",
        usage_metric_key="monthly_helper_runs",
    ),
    "brand_voice_validator": HelperToolDefinition(
        name="brand_voice_validator",
        is_advanced=True,
        required_feature_key="advanced_ai_helpers",
        usage_metric_key="monthly_advanced_helper_runs",
    ),
    "cross_channel_adaptation": HelperToolDefinition(
        name="cross_channel_adaptation",
        is_advanced=True,
        required_feature_key="advanced_ai_helpers",
        usage_metric_key="monthly_advanced_helper_runs",
    ),
    "template_recommendation": HelperToolDefinition(
        name="template_recommendation",
        is_advanced=True,
        required_feature_key="advanced_ai_helpers",
        usage_metric_key="monthly_advanced_helper_runs",
    ),
    "asset_recommendation": HelperToolDefinition(
        name="asset_recommendation",
        is_advanced=True,
        required_feature_key="advanced_ai_helpers",
        usage_metric_key="monthly_advanced_helper_runs",
    ),
    "review_feedback_to_revision_checklist": HelperToolDefinition(
        name="review_feedback_to_revision_checklist",
        is_advanced=True,
        required_feature_key="advanced_ai_helpers",
        usage_metric_key="monthly_advanced_helper_runs",
    ),
}

ADVANCED_HELPER_TOOL_NAMES = {
    name for name, definition in HELPER_TOOL_DEFINITIONS.items() if definition.is_advanced
}


def get_helper_tool_definition(tool_name: str) -> HelperToolDefinition:
    try:
        return HELPER_TOOL_DEFINITIONS[tool_name]
    except KeyError as exc:
        raise LookupError(f"Helper tool '{tool_name}' is not registered.") from exc
