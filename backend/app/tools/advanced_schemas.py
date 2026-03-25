from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.enums import DraftReviewAction
from app.tools.schemas import ValidationCheckResult


class AdvancedDraftContextInput(BaseModel):
    draft_id: int | None = None
    brand_id: int | None = None
    campaign_id: int | None = None
    title: str | None = Field(default=None, max_length=255)
    platform: str | None = Field(default=None, max_length=120)
    content_type: str | None = Field(default=None, max_length=120)
    content_body: str | None = None


class AdvancedToolContext(BaseModel):
    draft_id: int | None = None
    brand_id: int
    brand_name: str
    campaign_id: int | None = None
    campaign_name: str | None = None
    title: str | None = None
    platform: str | None = None
    content_type: str | None = None


class BrandVoiceValidatorRequest(AdvancedDraftContextInput):
    pass


class BrandVoiceValidatorResponse(BaseModel):
    context: AdvancedToolContext
    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "warn", "fail"]
    summary: str
    aligned_traits: list[str]
    missing_traits: list[str]
    checks: list[ValidationCheckResult]
    revision_suggestions: list[str]


class CrossChannelAdaptationRequest(AdvancedDraftContextInput):
    source_platform: str | None = Field(default=None, max_length=120)
    target_platform: str = Field(min_length=2, max_length=120)
    preserve_call_to_action: bool = True
    include_hashtags: bool = True


class CrossChannelAdaptationResponse(BaseModel):
    context: AdvancedToolContext
    source_platform: str
    target_platform: str
    adapted_title: str | None = None
    adapted_body: str
    recommended_content_type: str | None = None
    adaptation_notes: list[str]
    warnings: list[str]
    derived_hashtags: list[str]


class TemplateRecommendationRequest(AdvancedDraftContextInput):
    limit: int = Field(default=5, ge=1, le=20)


class TemplateRecommendationItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    template_type: str
    platform: str | None = None
    content_type: str | None = None
    score: int = Field(ge=0, le=100)
    reasons: list[str]
    excerpt: str
    updated_at: datetime


class TemplateRecommendationResponse(BaseModel):
    context: AdvancedToolContext
    total_candidates: int
    recommendations: list[TemplateRecommendationItem]


class AssetRecommendationRequest(AdvancedDraftContextInput):
    limit: int = Field(default=5, ge=1, le=20)


class AssetRecommendationItem(BaseModel):
    id: int
    name: str
    asset_type: str
    file_url: str
    thumbnail_url: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    notes: str | None = None
    updated_at: datetime
    score: int = Field(ge=0, le=100)
    reasons: list[str]


class AssetRecommendationResponse(BaseModel):
    context: AdvancedToolContext
    total_candidates: int
    recommendations: list[AssetRecommendationItem]


class ReviewFeedbackToRevisionChecklistRequest(BaseModel):
    draft_id: int
    limit: int = Field(default=10, ge=1, le=25)


class RevisionChecklistItem(BaseModel):
    item: str
    priority: Literal["high", "medium", "low"]
    source_action: DraftReviewAction
    source_excerpt: str
    guidance: str


class ReviewFeedbackToRevisionChecklistResponse(BaseModel):
    context: AdvancedToolContext
    summary: str
    checklist_items: list[RevisionChecklistItem]
    preserved_strengths: list[str]
    source_comment_count: int
    blocker_count: int
