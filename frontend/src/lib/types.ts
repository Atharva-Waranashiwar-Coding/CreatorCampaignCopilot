export type BrandRole = "owner" | "admin" | "editor" | "reviewer" | "viewer";
export type MembershipStatus = "invited" | "active" | "suspended";
export type ProjectStatus = "active" | "archived";
export type CampaignStatus = "planning" | "active" | "completed" | "archived";
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

export type DraftReview = {
  id: number;
  draft_id: number;
  actor_user_id: number;
  actor_name: string | null;
  action: DraftReviewAction;
  comment: string | null;
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

export type CampaignOverview = {
  campaign: Campaign;
  brief: ContentBrief | null;
  drafts: ContentDraft[];
  status_breakdown: DraftStatusCount[];
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

export type DashboardSummary = {
  brand_count: number;
  project_count: number;
  campaign_count: number;
  active_campaign_count: number;
  draft_count: number;
  pending_review_count: number;
  approved_draft_count: number;
  recent_activity: AuditLog[];
};
