from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import BrandRole, PlanInterval, SubscriptionStatus
from app.schemas.audit_log import AuditLogRead


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    monthly_price_cents: int
    yearly_price_cents: int | None
    limits: dict[str, int | None]
    features: dict[str, bool]
    is_active: bool
    sort_order: int


class BrandSubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    brand_id: int
    plan_id: int
    plan_code: str
    plan_name: str
    status: SubscriptionStatus
    billing_interval: PlanInterval
    external_subscription_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    created_at: datetime
    updated_at: datetime


class UsageMetricRead(BaseModel):
    key: str
    label: str
    current: int
    limit: int | None
    remaining: int | None
    percent_used: int | None
    status: str


class FeatureAccessRead(BaseModel):
    key: str
    label: str
    description: str
    enabled: bool


class HelperToolPolicyRead(BaseModel):
    helper_tools_enabled: bool
    advanced_ai_helpers_enabled: bool
    helper_run_burst_limit: int | None
    helper_run_burst_window_minutes: int
    advanced_helper_run_burst_limit: int | None
    advanced_helper_run_burst_window_minutes: int


class BrandBillingSnapshotRead(BaseModel):
    brand_id: int
    brand_name: str
    current_user_role: BrandRole
    subscription: BrandSubscriptionRead
    current_plan: PlanRead
    available_plans: list[PlanRead]
    usage: list[UsageMetricRead]
    features: list[FeatureAccessRead]
    helper_policy: HelperToolPolicyRead
    upgrade_prompts: list[str]
    recent_plan_activity: list[AuditLogRead]


class BrandSubscriptionUpdate(BaseModel):
    plan_code: str = Field(min_length=2, max_length=80)
    billing_interval: PlanInterval = PlanInterval.MONTHLY
