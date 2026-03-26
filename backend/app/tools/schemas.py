from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import BrandRole, DraftReviewAction


class FetchBrandGuidelinesRequest(BaseModel):
    brand_id: int


class BrandGuidelinesResponse(BaseModel):
    brand_id: int
    brand_name: str
    slug: str
    current_user_role: BrandRole
    industry: str | None = None
    description: str | None = None
    tone_of_voice: str | None = None
    target_audience: str | None = None
    preferred_channels: list[str]
    guidelines_summary: str | None = None
    project_count: int
    campaign_count: int
    guidance_points: list[str]


class FetchTemplatesRequest(BaseModel):
    brand_id: int | None = None
    template_type: str | None = Field(default=None, max_length=80)
    platform: str | None = Field(default=None, max_length=120)
    content_type: str | None = Field(default=None, max_length=120)
    search: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class TemplateFilterSet(BaseModel):
    brand_id: int | None = None
    template_type: str | None = None
    platform: str | None = None
    content_type: str | None = None
    search: str | None = None
    limit: int


class TemplateSummary(BaseModel):
    id: int
    brand_id: int
    brand_name: str
    name: str
    description: str | None = None
    template_type: str
    platform: str | None = None
    content_type: str | None = None
    excerpt: str
    updated_at: datetime


class FetchTemplatesResponse(BaseModel):
    filters: TemplateFilterSet
    total: int
    returned: int
    templates: list[TemplateSummary]


class ValidationCheckResult(BaseModel):
    check: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class ValidateContentAgainstGuidelinesRequest(BaseModel):
    brand_id: int
    title: str | None = Field(default=None, max_length=255)
    platform: str | None = Field(default=None, max_length=120)
    content_type: str | None = Field(default=None, max_length=120)
    content_body: str = Field(min_length=1)
    template_id: int | None = None


class ValidateContentAgainstGuidelinesResponse(BaseModel):
    brand_id: int
    brand_name: str
    template_id: int | None = None
    template_name: str | None = None
    score: int = Field(ge=0, le=100)
    passed: bool
    summary: str
    matched_keywords: list[str]
    missing_keywords: list[str]
    checks: list[ValidationCheckResult]


class RetrieveCampaignAssetsRequest(BaseModel):
    campaign_id: int
    asset_type: str | None = Field(default=None, max_length=80)
    search: str | None = None


class CampaignAssetSummary(BaseModel):
    id: int
    name: str
    asset_type: str
    file_url: str
    thumbnail_url: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    notes: str | None = None
    updated_at: datetime


class RetrieveCampaignAssetsResponse(BaseModel):
    campaign_id: int
    campaign_name: str
    brand_id: int
    brand_name: str
    returned: int
    assets: list[CampaignAssetSummary]


class SummarizeReviewFeedbackRequest(BaseModel):
    draft_id: int
    limit: int = Field(default=5, ge=1, le=20)


class ReviewActionCount(BaseModel):
    action: DraftReviewAction
    count: int


class ReviewCommentSummary(BaseModel):
    actor_name: str | None = None
    action: DraftReviewAction
    comment: str
    created_at: datetime


class SummarizeReviewFeedbackResponse(BaseModel):
    draft_id: int
    draft_title: str
    brand_id: int
    brand_name: str
    current_status: str
    current_status_label: str
    current_user_role: BrandRole
    review_count: int
    latest_action: DraftReviewAction | None = None
    summary: str
    blockers: list[str]
    approvals: list[str]
    action_counts: list[ReviewActionCount]
    recent_comments: list[ReviewCommentSummary]


class HelperToolCatalogItem(BaseModel):
    name: str
    mcp_tool_name: str
    is_advanced: bool
    required_feature_key: str
    description: str
    rest_path: str
    http_method: str
    target_entity_type: str
    service_bindings: list[str]
    mcp_exposed: bool


class HelperToolCatalogResponse(BaseModel):
    mcp_helpers_enabled: bool
    mcp_runtime_available: bool
    mcp_http_transport_enabled: bool
    mcp_sse_transport_enabled: bool
    mcp_mount_path: str | None = None
    tools: list[HelperToolCatalogItem]
