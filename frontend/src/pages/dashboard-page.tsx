import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "../components/ui/button";
import { MetricCard } from "../components/shared/metric-card";
import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { useAuthStore } from "../features/auth/auth-store";
import { apiRequest } from "../lib/api";
import { formatDate, formatDateTime, formatStatusLabel } from "../lib/format";
import type {
  Brand,
  DashboardAnalytics,
  DashboardCampaignHealth,
  DashboardCampaignHealthReport,
  DashboardCountBucket,
  DashboardDateBucket,
  DashboardMemberBucket,
  DashboardRevisionCycleItem,
  DashboardSummary,
} from "../lib/types";

export function DashboardPage() {
  const token = useAuthStore((state) => state.token);
  const [brandFilter, setBrandFilter] = useState("all");
  const [mixInterval, setMixInterval] = useState<"week" | "month">("month");

  const brandsQuery = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiRequest<Brand[]>("/brands", {}, token),
  });

  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary", brandFilter],
    queryFn: () => apiRequest<DashboardSummary>(buildDashboardPath("/dashboard/summary", brandFilter), {}, token),
  });

  const analyticsQuery = useQuery({
    queryKey: ["dashboard-analytics", brandFilter, mixInterval],
    queryFn: () =>
      apiRequest<DashboardAnalytics>(
        buildDashboardPath("/dashboard/analytics", brandFilter, { interval: mixInterval }),
        {},
        token,
      ),
  });

  const campaignHealthQuery = useQuery({
    queryKey: ["dashboard-campaign-health", brandFilter],
    queryFn: () =>
      apiRequest<DashboardCampaignHealthReport>(
        buildDashboardPath("/dashboard/campaign-health", brandFilter),
        {},
        token,
      ),
  });

  const summary = summaryQuery.data;
  const analytics = analyticsQuery.data;
  const healthReport = campaignHealthQuery.data;
  const atRiskCampaignCount =
    (healthReport?.summary.at_risk_count ?? 0) + (healthReport?.summary.critical_count ?? 0);

  return (
    <div className="min-w-0">
      <PageHeader
        eyebrow="Dashboard"
        title="Campaign operating system"
        description="See health, workload, approvals, and launch pressure without opening every workspace."
        actions={(
          <Select
            className="min-w-[220px]"
            value={brandFilter}
            onChange={(event) => setBrandFilter(event.target.value)}
          >
            <option value="all">All accessible brands</option>
            {brandsQuery.data?.map((brand) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </Select>
        )}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          hint="Brands included in the current dashboard scope."
          label="Brands"
          value={summary?.brand_count ?? 0}
        />
        <MetricCard
          hint="Projects tied to the filtered brand scope."
          label="Projects"
          value={summary?.project_count ?? 0}
        />
        <MetricCard
          hint="Campaigns tracked across the selected workspace set."
          label="Campaigns"
          value={summary?.campaign_count ?? 0}
        />
        <MetricCard
          hint="Campaigns actively in motion right now."
          label="Active campaigns"
          value={summary?.active_campaign_count ?? 0}
        />
        <MetricCard
          hint="Drafts currently stored in the editorial pipeline."
          label="Drafts"
          value={summary?.draft_count ?? 0}
        />
        <MetricCard
          hint="Drafts still waiting on reviewer action."
          label="Pending review"
          value={summary?.pending_review_count ?? 0}
        />
        <MetricCard
          hint="Upcoming scheduled items in the current scope."
          label="Scheduled items"
          value={summary?.scheduled_item_count ?? 0}
        />
        <MetricCard
          hint="Reusable templates available to the selected brands."
          label="Templates"
          value={summary?.template_count ?? 0}
        />
        <MetricCard
          hint="Average campaign health score across the current dashboard scope."
          label="Avg health"
          value={Math.round(healthReport?.summary.average_score ?? 0)}
        />
        <MetricCard
          hint="Campaigns currently flagged as at risk or critical."
          label="At-risk campaigns"
          value={atRiskCampaignCount}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <HealthSummaryCard
          averageScore={healthReport?.summary.average_score ?? 0}
          criticalCount={healthReport?.summary.critical_count ?? 0}
          healthyCount={healthReport?.summary.healthy_count ?? 0}
          isLoading={campaignHealthQuery.isLoading}
          watchCount={healthReport?.summary.watch_count ?? 0}
          atRiskCount={healthReport?.summary.at_risk_count ?? 0}
        />
        <CampaignHealthListCard
          campaigns={healthReport?.campaigns ?? []}
          isLoading={campaignHealthQuery.isLoading}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-3">
        <MemberLoadCard
          eyebrow="Workload"
          items={analytics?.workload.drafts_by_member ?? []}
          isLoading={analyticsQuery.isLoading}
          subtitle="Open draft assignments by team member, including overdue and due-soon load."
          title="Draft ownership"
        />
        <MemberLoadCard
          eyebrow="Reviews"
          items={analytics?.workload.pending_reviews_by_reviewer ?? []}
          isLoading={analyticsQuery.isLoading}
          subtitle="Open review-task assignments routed to reviewers."
          title="Reviewer queue"
        />
        <BottleneckCard
          isLoading={analyticsQuery.isLoading}
          items={analytics?.workload.bottlenecks_by_status ?? []}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <ApprovalInsightsCard
          approvals={analytics?.approvals}
          isLoading={analyticsQuery.isLoading}
        />
        <RevisionCyclesCard
          drafts={analytics?.approvals.drafts_with_multiple_revision_cycles ?? []}
          isLoading={analyticsQuery.isLoading}
          totalCount={analytics?.approvals.multi_revision_draft_count ?? 0}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <BreakdownCard
          eyebrow="Campaigns"
          title="Status mix"
          subtitle={`${analytics?.campaigns.total ?? 0} total campaigns with ${analytics?.campaigns.active_count ?? 0} currently active.`}
          buckets={analytics?.campaigns.by_status ?? []}
          isLoading={analyticsQuery.isLoading}
        />
        <BreakdownCard
          eyebrow="Drafts"
          title="Pipeline pressure"
          subtitle={`${analytics?.drafts.pending_review_count ?? 0} in review and ${analytics?.drafts.approved_count ?? 0} approved.`}
          buckets={analytics?.drafts.by_status ?? []}
          isLoading={analyticsQuery.isLoading}
        />
        <BreakdownCard
          eyebrow="Reviews"
          title="Recent review actions"
          subtitle={`Activity over the last ${analytics?.reviews.recent_window_days ?? 14} days.`}
          buckets={analytics?.reviews.recent_actions ?? []}
          isLoading={analyticsQuery.isLoading}
        />
        <TimelineCard
          eyebrow="Schedule"
          title="Upcoming calendar load"
          subtitle={`${analytics?.schedule.upcoming_count ?? 0} upcoming items and ${analytics?.schedule.overdue_count ?? 0} overdue scheduled items.`}
          buckets={analytics?.schedule.upcoming_by_day ?? []}
          isLoading={analyticsQuery.isLoading}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <BreakdownCard
          eyebrow="Content mix"
          title="Platforms in flight"
          subtitle="Where current draft output is concentrated by channel."
          buckets={analytics?.content_mix.by_platform ?? []}
          isLoading={analyticsQuery.isLoading}
        />
        <BreakdownCard
          eyebrow="Content mix"
          title="Content types in flight"
          subtitle="What kinds of deliverables are being produced."
          buckets={analytics?.content_mix.by_content_type ?? []}
          isLoading={analyticsQuery.isLoading}
        />
        <BreakdownCard
          eyebrow="Content mix"
          title="Drafts by campaign status"
          subtitle="How content production maps onto campaign execution state."
          buckets={analytics?.content_mix.by_campaign_status ?? []}
          isLoading={analyticsQuery.isLoading}
        />
        <div>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Content mix</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Output over time</h2>
            </div>
            <div className="inline-flex rounded-full bg-muted/70 p-1">
              {(["week", "month"] as const).map((interval) => (
                <Button
                  key={interval}
                  className={mixInterval === interval ? "" : "bg-transparent text-foreground hover:bg-white/60"}
                  onClick={() => setMixInterval(interval)}
                  type="button"
                  variant={mixInterval === interval ? "primary" : "ghost"}
                >
                  {interval === "week" ? "Weekly" : "Monthly"}
                </Button>
              ))}
            </div>
          </div>
          <TimelineCard
            eyebrow="Volume"
            title="Draft creation trend"
            subtitle={`Draft count grouped by ${mixInterval === "week" ? "week" : "month"} using draft creation date.`}
            buckets={analytics?.content_mix.by_interval ?? []}
            isLoading={analyticsQuery.isLoading}
          />
        </div>
      </div>

      <Card className="mt-8 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Recent activity</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Audit trail basics</h2>
          </div>
          {summaryQuery.isFetching || analyticsQuery.isFetching || campaignHealthQuery.isFetching ? (
            <Badge tone="muted">Refreshing</Badge>
          ) : null}
        </div>

        {summaryQuery.isLoading ? (
          <p className="mt-6 text-sm text-muted-foreground">Loading dashboard activity...</p>
        ) : summary?.recent_activity.length ? (
          <div className="mt-6 space-y-3">
            {summary.recent_activity.map((item) => (
              <div
                key={item.id}
                className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4"
              >
                <div className="flex flex-wrap items-center gap-3">
                  <Badge>{item.entity_type}</Badge>
                  <p className="text-sm font-medium capitalize text-foreground">
                    {item.action.replace(/[._]/g, " ")}
                  </p>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {item.actor_name ?? "Unknown user"} · {formatDateTime(item.created_at)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-6 text-sm text-muted-foreground">
            Activity will appear here once campaigns, drafts, plan changes, and template actions start moving through the workspace.
          </p>
        )}
      </Card>
    </div>
  );
}

function HealthSummaryCard({
  averageScore,
  healthyCount,
  watchCount,
  atRiskCount,
  criticalCount,
  isLoading,
}: {
  averageScore: number;
  healthyCount: number;
  watchCount: number;
  atRiskCount: number;
  criticalCount: number;
  isLoading: boolean;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Campaign health</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">Portfolio score</h2>
      <p className="mt-3 text-sm text-muted-foreground">
        Transparent scoring starts at 100 and subtracts penalties for overdue drafts, pending approvals, missing assets, unassigned work, and near-term deadline pressure.
      </p>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading campaign health...</p>
      ) : (
        <div className="mt-6">
          <div className="flex items-end gap-4">
            <p className="text-5xl font-semibold tracking-tight">{Math.round(averageScore)}</p>
            <Badge tone={healthTone(averageScore >= 85 ? "healthy" : averageScore >= 70 ? "watch" : averageScore >= 50 ? "at_risk" : "critical")}>
              average score
            </Badge>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
            <HealthCountPill label="Healthy" tone="success" value={healthyCount} />
            <HealthCountPill label="Watch" tone="warning" value={watchCount} />
            <HealthCountPill label="At risk" tone="warning" value={atRiskCount} />
            <HealthCountPill label="Critical" tone="warning" value={criticalCount} />
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <HealthLegendItem label="Healthy" range="85-100" description="No major workflow pressure is active." />
            <HealthLegendItem label="Watch" range="70-84" description="Some delivery risk is building but still manageable." />
            <HealthLegendItem label="At risk" range="50-69" description="The campaign needs intervention to avoid slippage." />
            <HealthLegendItem label="Critical" range="0-49" description="Multiple health penalties are compounding at once." />
          </div>
        </div>
      )}
    </Card>
  );
}

function CampaignHealthListCard({
  campaigns,
  isLoading,
}: {
  campaigns: DashboardCampaignHealth[];
  isLoading: boolean;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Campaign health</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Why scores moved</h2>
        </div>
        <Badge tone="muted">{campaigns.length} campaigns</Badge>
      </div>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading scored campaigns...</p>
      ) : campaigns.length ? (
        <div className="mt-6 space-y-4">
          {campaigns.slice(0, 6).map((campaign) => (
            <div key={campaign.campaign_id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link className="text-base font-semibold text-foreground hover:text-primary" to={`/campaigns/${campaign.campaign_id}`}>
                      {campaign.campaign_name}
                    </Link>
                    <Badge tone={healthTone(campaign.label)}>{campaign.label.replace("_", " ")}</Badge>
                    <Badge tone="muted">{campaign.project_name}</Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {campaign.brand_name} · {formatStatusLabel(campaign.campaign_status)}
                    {campaign.next_deadline_at ? ` · Next deadline ${formatDateTime(campaign.next_deadline_at)}` : ""}
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-3xl font-semibold tracking-tight">{campaign.score}</p>
                  <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">score</p>
                </div>
              </div>

              <div className="mt-4 h-2 rounded-full bg-slate-200/80">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(12,86,102,0.95),rgba(26,132,153,0.85))]"
                  style={{ width: `${campaign.score}%` }}
                />
              </div>

              {campaign.factors.length ? (
                <div className="mt-4 space-y-2">
                  {campaign.factors.map((factor) => (
                    <div key={factor.key} className="rounded-[1rem] border border-amber-200 bg-amber-50/70 px-3 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone="warning">-{factor.penalty}</Badge>
                        <p className="text-sm font-medium text-foreground">
                          {factor.label} · {factor.count}
                        </p>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{factor.detail}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted-foreground">
                  No active health penalties. The campaign has no overdue, approval, asset, assignment, or deadline pressure flags.
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">Campaign health will appear here once campaigns exist in the current scope.</p>
      )}
    </Card>
  );
}

function MemberLoadCard({
  eyebrow,
  items,
  isLoading,
  subtitle,
  title,
}: {
  eyebrow: string;
  items: DashboardMemberBucket[];
  isLoading: boolean;
  subtitle: string;
  title: string;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
      <p className="mt-3 text-sm text-muted-foreground">{subtitle}</p>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading workload...</p>
      ) : items.length ? (
        <div className="mt-6 space-y-3">
          {items.map((item) => (
            <div key={`${item.user_id}-${item.email}`} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">{item.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{item.email}</p>
                </div>
                <Badge tone="muted">{item.count} open</Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge tone={item.overdue_count ? "warning" : "muted"}>{item.overdue_count} overdue</Badge>
                <Badge tone={item.due_soon_count ? "warning" : "muted"}>{item.due_soon_count} due soon</Badge>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No open assignments are currently tracked in this section.</p>
      )}
    </Card>
  );
}

function BottleneckCard({
  items,
  isLoading,
}: {
  items: DashboardAnalytics["workload"]["bottlenecks_by_status"];
  isLoading: boolean;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Bottlenecks</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">Status drag</h2>
      <p className="mt-3 text-sm text-muted-foreground">
        Drafts grouped by current status, with stale counts based on drafts that have not moved in more than three days.
      </p>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading bottlenecks...</p>
      ) : items.length ? (
        <div className="mt-6 space-y-3">
          {items.map((item) => (
            <div key={item.status} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-foreground">{item.label}</p>
                <Badge tone="muted">{item.count}</Badge>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">{item.stale_count} stale in this status</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No draft bottlenecks are currently visible.</p>
      )}
    </Card>
  );
}

function ApprovalInsightsCard({
  approvals,
  isLoading,
}: {
  approvals: DashboardAnalytics["approvals"] | undefined;
  isLoading: boolean;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Approval analytics</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">Turnaround and decision quality</h2>
      <p className="mt-3 text-sm text-muted-foreground">
        Review timing is calculated from `submitted` or `resubmitted` to the next approval or rejection event.
      </p>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading approval analytics...</p>
      ) : (
        <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Avg review time" value={`${approvals?.average_review_time_hours ?? 0}h`} />
          <StatCard label="Avg approval time" value={`${approvals?.average_approval_time_hours ?? 0}h`} />
          <StatCard label="Rejection rate" value={`${approvals?.rejection_rate ?? 0}%`} />
          <StatCard label="Decisions" value={approvals?.decision_count ?? 0} />
        </div>
      )}
    </Card>
  );
}

function RevisionCyclesCard({
  drafts,
  isLoading,
  totalCount,
}: {
  drafts: DashboardRevisionCycleItem[];
  isLoading: boolean;
  totalCount: number;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Revision cycles</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Drafts needing repeat loops</h2>
        </div>
        <Badge tone="muted">{totalCount} drafts</Badge>
      </div>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading revision history...</p>
      ) : drafts.length ? (
        <div className="mt-6 space-y-3">
          {drafts.map((draft) => (
            <div key={draft.draft_id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <Link className="text-sm font-semibold text-foreground hover:text-primary" to={`/drafts/${draft.draft_id}`}>
                    {draft.draft_title}
                  </Link>
                  <p className="mt-1 text-sm text-muted-foreground">{draft.campaign_name}</p>
                </div>
                <Badge tone={draft.rejection_count ? "warning" : "muted"}>
                  {draft.revision_cycle_count} cycles · {draft.rejection_count} rejections
                </Badge>
              </div>
              <p className="mt-3 text-sm text-muted-foreground">
                Current status: {formatStatusLabel(draft.status, draft.status_label)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No drafts have crossed multiple revision cycles yet.</p>
      )}
    </Card>
  );
}

function HealthCountPill({
  label,
  tone,
  value,
}: {
  label: string;
  tone: "success" | "warning" | "muted";
  value: number;
}) {
  return (
    <div className="rounded-[1.2rem] border border-border bg-white/80 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-2xl font-semibold tracking-tight">{value}</p>
        <Badge className="max-w-full" tone={tone}>{label}</Badge>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-[1.2rem] border border-border bg-white/80 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function HealthLegendItem({
  description,
  label,
  range,
}: {
  description: string;
  label: string;
  range: string;
}) {
  return (
    <div className="rounded-[1.15rem] border border-border bg-white/80 px-4 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-semibold text-foreground">{label}</p>
        <Badge tone={healthTone(label.toLowerCase().replace(" ", "_"))}>{range}</Badge>
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
    </div>
  );
}

function BreakdownCard({
  eyebrow,
  title,
  subtitle,
  buckets,
  isLoading,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  buckets: DashboardCountBucket[];
  isLoading: boolean;
}) {
  const maxCount = Math.max(...buckets.map((bucket) => bucket.count), 0);

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
      <p className="mt-3 text-sm text-muted-foreground">{subtitle}</p>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading analytics...</p>
      ) : buckets.length ? (
        <div className="mt-6 space-y-4">
          {buckets.map((bucket) => (
            <div key={bucket.key}>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span>{bucket.label}</span>
                <span className="font-medium text-foreground">{bucket.count}</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-200/80">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(12,86,102,0.95),rgba(26,132,153,0.85))]"
                  style={{
                    width: `${maxCount ? Math.max((bucket.count / maxCount) * 100, bucket.count ? 8 : 0) : 0}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No analytics in this section yet.</p>
      )}
    </Card>
  );
}

function TimelineCard({
  eyebrow,
  title,
  subtitle,
  buckets,
  isLoading,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  buckets: DashboardDateBucket[];
  isLoading: boolean;
}) {
  const maxCount = Math.max(...buckets.map((bucket) => bucket.count), 0);

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
      <p className="mt-3 text-sm text-muted-foreground">{subtitle}</p>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading schedule analytics...</p>
      ) : buckets.length ? (
        <div className="mt-6 space-y-4">
          {buckets.map((bucket) => (
            <div key={bucket.date}>
              <div className="flex items-center justify-between gap-3 text-sm">
                <span>{formatDate(bucket.date)}</span>
                <span className="font-medium text-foreground">{bucket.count}</span>
              </div>
              <div className="mt-2 h-2 rounded-full bg-slate-200/80">
                <div
                  className="h-full rounded-full bg-[linear-gradient(90deg,rgba(191,87,0,0.9),rgba(245,158,11,0.85))]"
                  style={{
                    width: `${maxCount ? Math.max((bucket.count / maxCount) * 100, bucket.count ? 8 : 0) : 0}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No scheduled items are currently queued in the next two weeks.</p>
      )}
    </Card>
  );
}

function buildDashboardPath(basePath: string, brandFilter: string, extraParams?: Record<string, string>) {
  const params = new URLSearchParams(extraParams);
  if (brandFilter !== "all") {
    params.set("brand_id", brandFilter);
  }
  if (!params.toString()) {
    return basePath;
  }
  return `${basePath}?${params.toString()}`;
}

function healthTone(label: string): "success" | "warning" | "muted" {
  if (label === "healthy") {
    return "success";
  }
  if (label === "watch" || label === "at_risk" || label === "critical") {
    return "warning";
  }
  return "muted";
}
