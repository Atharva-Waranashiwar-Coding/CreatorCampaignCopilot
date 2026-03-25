export type BrandRole = "owner" | "admin" | "editor" | "reviewer" | "viewer";
export type MembershipStatus = "invited" | "active" | "suspended";
export type ProjectStatus = "active" | "archived";
export type CampaignStatus = "planning" | "active" | "completed" | "archived";

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
  recent_activity: AuditLog[];
};
