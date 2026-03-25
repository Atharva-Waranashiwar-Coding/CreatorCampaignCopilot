export type BrandRole = "owner" | "admin" | "editor" | "reviewer" | "viewer";
export type MembershipStatus = "invited" | "active" | "suspended";
export type ProjectStatus = "active" | "archived";
export type CampaignStatus = "planning" | "active" | "completed" | "archived";
export type CommentEntityType = "campaign" | "draft";
export type AssignmentEntityType = "campaign" | "draft" | "review_task";
export type AssignmentStatus = "open" | "completed" | "canceled";
export type DraftStatus =
  | "idea"
  | "draft"
  | "in_review"
  | "approved"
  | "scheduled"
  | "published"
  | "rejected";
export type DraftReviewAction =
  | "commented"
  | "submitted"
  | "approved"
  | "rejected"
  | "resubmitted";
export type PlanInterval = "monthly" | "yearly";
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "canceled";
export type NotificationType =
  | "mention"
  | "review_requested"
  | "draft_approved"
  | "draft_rejected"
  | "assignment_created"
  | "due_soon";

export type User = {
  id: number;
  full_name: string;
  email: string;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: User;
};

export type Brand = {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  industry: string | null;
  tone_of_voice: string | null;
  target_audience: string | null;
  preferred_channels: string[];
  guidelines_summary: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
  current_user_role: BrandRole;
  membership_count: number;
  project_count: number;
  campaign_count: number;
};

export type Membership = {
  id: number;
  brand_id: number;
  user_id: number | null;
  invite_email: string;
  invited_by_id: number | null;
  role: BrandRole;
  status: MembershipStatus;
  invited_at: string;
  joined_at: string | null;
  created_at: string;
  updated_at: string;
  user: User | null;
};

export type Project = {
  id: number;
  brand_id: number;
  brand_name: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_by: number;
  created_at: string;
  updated_at: string;
  campaign_count: number;
};

export type Campaign = {
  id: number;
  project_id: number;
  project_name: string;
  brand_id: number;
  brand_name: string;
  name: string;
  objective: string | null;
  audience: string | null;
  campaign_type: string | null;
  start_date: string | null;
  end_date: string | null;
  status: CampaignStatus;
  created_by: number;
  created_at: string;
  updated_at: string;
  brief_id: number | null;
  draft_count: number;
};

export type ContentBrief = {
  id: number;
  campaign_id: number;
  key_message: string | null;
  call_to_action: string | null;
  tone: string | null;
  channels: string[];
  themes: string[];
  references: string | null;
  created_at: string;
  updated_at: string;
};

export type ContentDraft = {
  id: number;
  campaign_id: number;
  campaign_name: string;
  project_id: number;
  project_name: string;
  brand_id: number;
  brand_name: string;
  title: string;
  platform: string;
  content_type: string;
  content_body: string | null;
  status: DraftStatus;
  planned_publish_at: string | null;
  current_version_number: number;
  created_by: number;
  creator_name: string | null;
  review_count: number;
  latest_review_action: DraftReviewAction | null;
  latest_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CampaignAsset = {
  id: number;
  campaign_id: number;
  name: string;
  asset_type: string;
  file_url: string;
  thumbnail_url: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  notes: string | null;
  created_by: number;
  creator_name: string | null;
  created_at: string;
  updated_at: string;
};

export type Mention = {
  id: number;
  mentioned_user_id: number;
  mentioned_user_name: string;
  mentioned_user_email: string;
  identifier: string;
  created_at: string;
};

export type CollaborationComment = {
  id: number;
  brand_id: number;
  entity_type: CommentEntityType;
  entity_id: number;
  campaign_id: number | null;
  draft_id: number | null;
  parent_comment_id: number | null;
  author_user_id: number;
  author_name: string | null;
  body: string;
  mentions: Mention[];
  created_at: string;
  updated_at: string;
  replies: CollaborationComment[];
};

export type Assignment = {
  id: number;
  brand_id: number;
  assignment_type: AssignmentEntityType;
  campaign_id: number | null;
  draft_id: number | null;
  entity_id: number;
  assignee_user_id: number;
  assignee_name: string | null;
  assignee_email: string | null;
  assigned_by_user_id: number;
  assigned_by_name: string | null;
  note: string | null;
  due_at: string | null;
  status: AssignmentStatus;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DraftVersion = {
  id: number;
  draft_id: number;
  draft_title: string;
  campaign_id: number;
  campaign_name: string;
  project_id: number;
  project_name: string;
  brand_id: number;
  brand_name: string;
  version_number: number;
  title: string;
  platform: string;
  content_type: string;
  content_body: string | null;
  status: DraftStatus;
  planned_publish_at: string | null;
  change_summary: string | null;
  created_by: number;
  creator_name: string | null;
  created_at: string;
};

export type CalendarItem = {
  id: number;
  brand_id: number;
  brand_name: string;
  campaign_id: number;
  campaign_name: string;
  draft_id: number | null;
  draft_title: string | null;
  title: string;
  platform: string | null;
  item_type: string;
  scheduled_for: string;
  status: string | null;
  notes: string | null;
  created_by: number;
  creator_name: string | null;
  created_at: string;
  updated_at: string;
};

export type DraftReview = {
  id: number;
  draft_id: number;
  actor_user_id: number;
  actor_name: string | null;
  action: DraftReviewAction;
  comment: string | null;
  mentions: Mention[];
  version_number: number;
  from_status: DraftStatus | null;
  to_status: DraftStatus | null;
  created_at: string;
};

export type DraftReviewThread = {
  draft_id: number;
  current_user_role: BrandRole;
  available_actions: DraftReviewAction[];
  reviews: DraftReview[];
};

export type DraftStatusCount = {
  status: DraftStatus;
  count: number;
};

export type CampaignPlanningSummary = {
  total_drafts: number;
  idea_count: number;
  draft_count: number;
  in_review_count: number;
  approved_count: number;
  scheduled_count: number;
  published_count: number;
  rejected_count: number;
  next_planned_publish_at: string | null;
};

export type CampaignOverview = {
  campaign: Campaign;
  brief: ContentBrief | null;
  drafts: ContentDraft[];
  assets: CampaignAsset[];
  recent_versions: DraftVersion[];
  schedule: CalendarItem[];
  status_breakdown: DraftStatusCount[];
  planning_summary: CampaignPlanningSummary;
  activity_timeline: AuditLog[];
};

export type AuditLog = {
  id: number;
  brand_id: number;
  actor_user_id: number;
  actor_name: string | null;
  entity_type: string;
  entity_id: number;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type DashboardCountBucket = {
  key: string;
  label: string;
  count: number;
};

export type DashboardDateBucket = {
  date: string;
  count: number;
};

export type DashboardHealthFactor = {
  key: string;
  label: string;
  count: number;
  penalty: number;
  detail: string;
};

export type DashboardMemberBucket = {
  user_id: number;
  name: string;
  email: string;
  count: number;
  overdue_count: number;
  due_soon_count: number;
};

export type DashboardStatusBottleneck = {
  status: DraftStatus;
  label: string;
  count: number;
  stale_count: number;
};

export type DashboardSummary = {
  brand_count: number;
  project_count: number;
  campaign_count: number;
  active_campaign_count: number;
  draft_count: number;
  pending_review_count: number;
  approved_draft_count: number;
  scheduled_item_count: number;
  template_count: number;
  recent_activity: AuditLog[];
};

export type DashboardCampaignAnalytics = {
  total: number;
  active_count: number;
  by_status: DashboardCountBucket[];
};

export type DashboardDraftAnalytics = {
  total: number;
  pending_review_count: number;
  approved_count: number;
  by_status: DashboardCountBucket[];
};

export type DashboardReviewAnalytics = {
  pending_count: number;
  recent_window_days: number;
  recent_actions: DashboardCountBucket[];
};

export type DashboardScheduleAnalytics = {
  upcoming_count: number;
  overdue_count: number;
  upcoming_by_day: DashboardDateBucket[];
};

export type DashboardWorkloadAnalytics = {
  drafts_by_member: DashboardMemberBucket[];
  pending_reviews_by_reviewer: DashboardMemberBucket[];
  bottlenecks_by_status: DashboardStatusBottleneck[];
};

export type DashboardRevisionCycleItem = {
  draft_id: number;
  draft_title: string;
  campaign_id: number;
  campaign_name: string;
  revision_cycle_count: number;
  rejection_count: number;
  status: DraftStatus;
};

export type DashboardApprovalAnalytics = {
  average_review_time_hours: number;
  average_approval_time_hours: number;
  rejection_rate: number;
  decision_count: number;
  drafts_with_multiple_revision_cycles: DashboardRevisionCycleItem[];
  multi_revision_draft_count: number;
};

export type DashboardContentMixAnalytics = {
  interval: string;
  by_platform: DashboardCountBucket[];
  by_content_type: DashboardCountBucket[];
  by_campaign_status: DashboardCountBucket[];
  by_interval: DashboardDateBucket[];
};

export type DashboardCampaignHealth = {
  campaign_id: number;
  campaign_name: string;
  project_id: number;
  project_name: string;
  brand_id: number;
  brand_name: string;
  campaign_status: string;
  score: number;
  label: string;
  penalty_total: number;
  draft_count: number;
  asset_count: number;
  next_deadline_at: string | null;
  factors: DashboardHealthFactor[];
};

export type DashboardCampaignHealthSummary = {
  average_score: number;
  healthy_count: number;
  watch_count: number;
  at_risk_count: number;
  critical_count: number;
};

export type DashboardCampaignHealthReport = {
  summary: DashboardCampaignHealthSummary;
  campaigns: DashboardCampaignHealth[];
};

export type DashboardAnalytics = {
  campaigns: DashboardCampaignAnalytics;
  drafts: DashboardDraftAnalytics;
  reviews: DashboardReviewAnalytics;
  schedule: DashboardScheduleAnalytics;
  workload: DashboardWorkloadAnalytics;
  approvals: DashboardApprovalAnalytics;
  content_mix: DashboardContentMixAnalytics;
};

export type ContentTemplate = {
  id: number;
  brand_id: number;
  brand_name: string;
  name: string;
  description: string | null;
  template_type: string;
  platform: string | null;
  content_type: string | null;
  body: string;
  created_by: number;
  creator_name: string | null;
  created_at: string;
  updated_at: string;
};

export type Plan = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  monthly_price_cents: number;
  yearly_price_cents: number | null;
  limits: Record<string, number | null>;
  features: Record<string, boolean>;
  is_active: boolean;
  sort_order: number;
};

export type BrandSubscription = {
  id: number;
  brand_id: number;
  plan_id: number;
  plan_code: string;
  plan_name: string;
  status: SubscriptionStatus;
  billing_interval: PlanInterval;
  external_subscription_id: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
  updated_at: string;
};

export type UsageMetric = {
  key: string;
  label: string;
  current: number;
  limit: number | null;
  remaining: number | null;
  percent_used: number | null;
  status: string;
};

export type FeatureAccess = {
  key: string;
  label: string;
  description: string;
  enabled: boolean;
};

export type HelperToolCatalogItem = {
  name: string;
  mcp_tool_name: string;
  description: string;
  rest_path: string;
  http_method: string;
  target_entity_type: string;
  service_bindings: string[];
  mcp_exposed: boolean;
};

export type HelperToolCatalog = {
  mcp_helpers_enabled: boolean;
  mcp_runtime_available: boolean;
  mcp_http_transport_enabled: boolean;
  mcp_sse_transport_enabled: boolean;
  mcp_mount_path: string | null;
  tools: HelperToolCatalogItem[];
};

export type ToolUsageLog = {
  id: number;
  tool_name: string;
  actor_user_id: number;
  actor_name: string | null;
  brand_id: number | null;
  brand_name: string | null;
  target_entity_type: string;
  target_entity_id: number | null;
  invocation_source: string;
  was_successful: boolean;
  error_detail: string | null;
  request_payload: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  created_at: string;
};

export type Notification = {
  id: number;
  user_id: number;
  brand_id: number;
  actor_user_id: number | null;
  actor_name: string | null;
  notification_type: NotificationType;
  title: string;
  body: string;
  entity_type: string;
  entity_id: number | null;
  metadata: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
};

export type NotificationSummary = {
  unread_count: number;
  recent_unread: Notification[];
};

export type BrandBillingSnapshot = {
  brand_id: number;
  brand_name: string;
  current_user_role: BrandRole;
  subscription: BrandSubscription;
  current_plan: Plan;
  available_plans: Plan[];
  usage: UsageMetric[];
  features: FeatureAccess[];
  upgrade_prompts: string[];
  recent_plan_activity: AuditLog[];
};
