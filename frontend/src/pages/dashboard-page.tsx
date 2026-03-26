import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
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
  CampaignOverview,
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
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null);

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
  const campaignFocusOptions = healthReport?.campaigns ?? [];

  useEffect(() => {
    if (!campaignFocusOptions.length) {
      setSelectedCampaignId(null);
      return;
    }

    if (!selectedCampaignId || !campaignFocusOptions.some((campaign) => campaign.campaign_id === selectedCampaignId)) {
      setSelectedCampaignId(campaignFocusOptions[0].campaign_id);
    }
  }, [campaignFocusOptions, selectedCampaignId]);

  const selectedCampaignHealth = campaignFocusOptions.find((campaign) => campaign.campaign_id === selectedCampaignId) ?? null;

  const selectedCampaignOverviewQuery = useQuery({
    queryKey: ["dashboard-campaign-overview", selectedCampaignId],
    queryFn: () => apiRequest<CampaignOverview>(`/campaigns/${selectedCampaignId}/overview`, {}, token),
    enabled: Boolean(selectedCampaignId),
  });

  const selectedCampaignBottlenecks = selectedCampaignOverviewQuery.data
    ? buildCampaignBottlenecks(selectedCampaignOverviewQuery.data)
    : [];

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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
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

      <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,0.96fr)_minmax(0,1.04fr)]">
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
          selectedCampaign={selectedCampaignHealth}
          selectedCampaignId={selectedCampaignId}
          onSelectedCampaignChange={setSelectedCampaignId}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,0.98fr)_minmax(0,1.02fr)]">
        <div className="grid gap-6">
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
        </div>
        <BottleneckCard
          campaigns={healthReport?.campaigns ?? []}
          isLoading={campaignHealthQuery.isLoading || selectedCampaignOverviewQuery.isLoading}
          items={selectedCampaignBottlenecks}
          selectedCampaign={selectedCampaignHealth}
          selectedCampaignId={selectedCampaignId}
          onSelectedCampaignChange={setSelectedCampaignId}
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
        <div className="grid gap-6">
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
        </div>
        <div className="grid gap-6">
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
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <div className="grid gap-6">
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
        </div>
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
          <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
            <ScoreGauge
              label="Average health"
              tone={healthTone(averageScore >= 85 ? "healthy" : averageScore >= 70 ? "watch" : averageScore >= 50 ? "at_risk" : "critical")}
              value={averageScore}
            />

            <div>
              <div className="flex flex-wrap items-center gap-3">
                <p className="text-5xl font-semibold tracking-tight">{Math.round(averageScore)}</p>
                <Badge tone={healthTone(averageScore >= 85 ? "healthy" : averageScore >= 70 ? "watch" : averageScore >= 50 ? "at_risk" : "critical")}>
                  average score
                </Badge>
              </div>

              <p className="mt-4 text-sm leading-6 text-muted-foreground">
                Health distribution gives a faster read on whether the portfolio is clustered in healthy execution or getting pulled toward watch, risk, and critical states.
              </p>

              <HealthDistributionBar
                atRiskCount={atRiskCount}
                criticalCount={criticalCount}
                healthyCount={healthyCount}
                watchCount={watchCount}
              />
            </div>
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
  selectedCampaign,
  selectedCampaignId,
  onSelectedCampaignChange,
}: {
  campaigns: DashboardCampaignHealth[];
  isLoading: boolean;
  selectedCampaign: DashboardCampaignHealth | null;
  selectedCampaignId: number | null;
  onSelectedCampaignChange: (campaignId: number) => void;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Campaign health</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Why scores moved</h2>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-3">
          <Badge tone="muted">{campaigns.length} campaigns</Badge>
          <CampaignFocusSelect
            campaigns={campaigns}
            selectedCampaignId={selectedCampaignId}
            onChange={onSelectedCampaignChange}
          />
        </div>
      </div>

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading scored campaigns...</p>
      ) : selectedCampaign ? (
        <div className="mt-6">
          <div className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Link className="text-base font-semibold text-foreground hover:text-primary" to={`/campaigns/${selectedCampaign.campaign_id}`}>
                    {selectedCampaign.campaign_name}
                  </Link>
                  <Badge tone={healthTone(selectedCampaign.label)}>{selectedCampaign.label.replace("_", " ")}</Badge>
                  <Badge tone="muted">{selectedCampaign.project_name}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {selectedCampaign.brand_name} · {formatStatusLabel(selectedCampaign.campaign_status)}
                  {selectedCampaign.next_deadline_at ? ` · Next deadline ${formatDateTime(selectedCampaign.next_deadline_at)}` : ""}
                </p>
              </div>

              <div className="text-right">
                <p className="text-3xl font-semibold tracking-tight">{selectedCampaign.score}</p>
                <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">score</p>
              </div>
            </div>

            <div className="mt-4 h-2 rounded-full bg-slate-200/80">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,rgba(12,86,102,0.95),rgba(26,132,153,0.85))]"
                style={{ width: `${selectedCampaign.score}%` }}
              />
            </div>

            {selectedCampaign.factors.length ? (
              <div className="mt-4 space-y-2">
                {selectedCampaign.factors.map((factor) => (
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
                No active health penalties. This campaign has no overdue, approval, asset, assignment, or deadline pressure flags.
              </p>
            )}
          </div>
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
  const maxCount = Math.max(...items.map((item) => item.count), 0);

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
              <div className="mt-4">
                <MemberLoadBar item={item} maxCount={maxCount} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
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
  campaigns,
  items,
  isLoading,
  selectedCampaign,
  selectedCampaignId,
  onSelectedCampaignChange,
}: {
  campaigns: DashboardCampaignHealth[];
  items: DashboardAnalytics["workload"]["bottlenecks_by_status"];
  isLoading: boolean;
  selectedCampaign: DashboardCampaignHealth | null;
  selectedCampaignId: number | null;
  onSelectedCampaignChange: (campaignId: number) => void;
}) {
  const maxCount = Math.max(...items.map((item) => item.count), 0);

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Bottlenecks</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Status drag</h2>
          <p className="mt-3 text-sm text-muted-foreground">
            Drafts grouped by current status for the selected campaign, with stale counts based on drafts that have not moved in more than three days.
          </p>
        </div>
        <CampaignFocusSelect
          campaigns={campaigns}
          selectedCampaignId={selectedCampaignId}
          onChange={onSelectedCampaignChange}
        />
      </div>

      {selectedCampaign ? (
        <p className="mt-4 text-sm text-muted-foreground">
          {selectedCampaign.campaign_name} · {selectedCampaign.project_name} · {selectedCampaign.brand_name}
        </p>
      ) : null}

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading bottlenecks...</p>
      ) : items.length ? (
        <div className="mt-6 space-y-3">
          {items.map((item) => (
            <div key={item.status} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-semibold text-foreground">{item.label}</p>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="muted">{item.count} total</Badge>
                  <Badge tone={item.stale_count ? "warning" : "muted"}>{item.stale_count} stale</Badge>
                </div>
              </div>
              <div className="mt-4">
                <BottleneckBar item={item} maxCount={maxCount} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No draft bottlenecks are currently visible for this campaign.</p>
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
  const maxTime = Math.max(
    approvals?.average_review_time_hours ?? 0,
    approvals?.average_approval_time_hours ?? 0,
    24,
  );

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
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <InsightMeterCard
            accentClassName="bg-[linear-gradient(90deg,rgba(12,86,102,0.95),rgba(26,132,153,0.85))]"
            label="Avg review time"
            progress={buildProgress(approvals?.average_review_time_hours ?? 0, maxTime)}
            value={`${approvals?.average_review_time_hours ?? 0}h`}
          />
          <InsightMeterCard
            accentClassName="bg-[linear-gradient(90deg,rgba(27,94,32,0.92),rgba(74,222,128,0.78))]"
            label="Avg approval time"
            progress={buildProgress(approvals?.average_approval_time_hours ?? 0, maxTime)}
            value={`${approvals?.average_approval_time_hours ?? 0}h`}
          />
          <InsightMeterCard
            accentClassName="bg-[linear-gradient(90deg,rgba(191,87,0,0.9),rgba(245,158,11,0.85))]"
            label="Rejection rate"
            progress={Math.min(approvals?.rejection_rate ?? 0, 100)}
            value={`${approvals?.rejection_rate ?? 0}%`}
          />
          <InsightMeterCard
            accentClassName="bg-[linear-gradient(90deg,rgba(67,56,202,0.9),rgba(96,165,250,0.8))]"
            label="Decisions"
            progress={buildProgress(approvals?.decision_count ?? 0, Math.max(approvals?.decision_count ?? 0, 12))}
            value={approvals?.decision_count ?? 0}
          />
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
              <div className="mt-4 flex flex-wrap gap-2">
                {buildCycleDots(draft.revision_cycle_count).map((dot, index) => (
                  <span
                    key={`${draft.draft_id}-dot-${index}`}
                    className={[
                      "h-3 w-3 rounded-full",
                      dot ? "bg-primary shadow-sm shadow-primary/30" : "bg-slate-200",
                    ].join(" ")}
                  />
                ))}
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
        <div className="mt-6">
          <div className="flex min-h-[220px] items-end gap-3 rounded-[1.4rem] border border-border bg-white/70 px-4 py-5">
            {buckets.map((bucket) => (
              <div key={bucket.date} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-3">
                <div className="text-xs font-semibold text-foreground">{bucket.count}</div>
                <div className="flex h-36 w-full items-end">
                  <div
                    className="w-full rounded-t-[1rem] bg-[linear-gradient(180deg,rgba(251,191,36,0.95),rgba(191,87,0,0.9))] shadow-[0_16px_28px_-22px_rgba(191,87,0,0.8)]"
                    style={{
                      height: `${maxCount ? Math.max((bucket.count / maxCount) * 100, bucket.count ? 10 : 0) : 0}%`,
                    }}
                  />
                </div>
                <div className="text-center text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground">
                  {formatTimelineLabel(bucket.date)}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-6 text-sm text-muted-foreground">No scheduled items are currently queued in the next two weeks.</p>
      )}
    </Card>
  );
}

function ScoreGauge({
  label,
  tone,
  value,
}: {
  label: string;
  tone: "success" | "warning" | "muted";
  value: number;
}) {
  const normalized = Math.max(0, Math.min(Math.round(value), 100));
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (normalized / 100) * circumference;
  const strokeClassName =
    tone === "success"
      ? "stroke-emerald-500"
      : tone === "warning"
        ? "stroke-amber-500"
        : "stroke-slate-500";

  return (
    <div className="flex flex-col items-center justify-center rounded-[1.5rem] border border-border bg-white/80 px-4 py-5">
      <div className="relative h-36 w-36">
        <svg className="-rotate-90" height="144" width="144">
          <circle className="fill-none stroke-slate-200" cx="72" cy="72" r={radius} strokeWidth="12" />
          <circle
            className={`fill-none ${strokeClassName}`}
            cx="72"
            cy="72"
            r={radius}
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            strokeLinecap="round"
            strokeWidth="12"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-4xl font-semibold tracking-tight">{normalized}</p>
          <p className="mt-1 text-[0.68rem] uppercase tracking-[0.18em] text-muted-foreground">score</p>
        </div>
      </div>
      <p className="mt-3 text-sm font-semibold text-foreground">{label}</p>
    </div>
  );
}

function HealthDistributionBar({
  healthyCount,
  watchCount,
  atRiskCount,
  criticalCount,
}: {
  healthyCount: number;
  watchCount: number;
  atRiskCount: number;
  criticalCount: number;
}) {
  const total = healthyCount + watchCount + atRiskCount + criticalCount;
  const segments = [
    { label: "Healthy", value: healthyCount, className: "bg-emerald-500" },
    { label: "Watch", value: watchCount, className: "bg-amber-300" },
    { label: "At risk", value: atRiskCount, className: "bg-amber-500" },
    { label: "Critical", value: criticalCount, className: "bg-rose-500" },
  ];

  return (
    <div className="mt-6">
      <div className="h-4 overflow-hidden rounded-full bg-slate-200/80">
        <div className="flex h-full w-full">
          {segments.map((segment) => (
            <div
              key={segment.label}
              className={segment.className}
              style={{ width: `${total ? (segment.value / total) * 100 : 0}%` }}
            />
          ))}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-3">
        {segments.map((segment) => (
          <div key={segment.label} className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className={`h-3 w-3 rounded-full ${segment.className}`} />
            <span>{segment.label}</span>
            <span className="font-semibold text-foreground">{segment.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MemberLoadBar({
  item,
  maxCount,
}: {
  item: DashboardMemberBucket;
  maxCount: number;
}) {
  const activeWidth = maxCount ? Math.max((item.count / maxCount) * 100, item.count ? 8 : 0) : 0;
  const safeCount = item.count || 1;
  const overdueWidth = (item.overdue_count / safeCount) * 100;
  const dueSoonWidth = (item.due_soon_count / safeCount) * 100;
  const plannedWidth = Math.max(100 - overdueWidth - dueSoonWidth, 0);

  return (
    <div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-200/80">
        <div className="flex h-full" style={{ width: `${activeWidth}%` }}>
          <div className="bg-rose-500" style={{ width: `${overdueWidth}%` }} />
          <div className="bg-amber-400" style={{ width: `${dueSoonWidth}%` }} />
          <div className="bg-primary/80" style={{ width: `${plannedWidth}%` }} />
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[0.7rem] uppercase tracking-[0.14em] text-muted-foreground">
        <span>Overdue</span>
        <span>Due soon</span>
        <span>Planned</span>
      </div>
    </div>
  );
}

function BottleneckBar({
  item,
  maxCount,
}: {
  item: DashboardAnalytics["workload"]["bottlenecks_by_status"][number];
  maxCount: number;
}) {
  const totalWidth = maxCount ? Math.max((item.count / maxCount) * 100, item.count ? 8 : 0) : 0;
  const staleWidth = item.count ? (item.stale_count / item.count) * totalWidth : 0;

  return (
    <div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-200/80">
        <div className="relative h-full rounded-full bg-primary/20" style={{ width: `${totalWidth}%` }}>
          <div className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${Math.max(totalWidth - staleWidth, 0)}%` }} />
          <div className="absolute inset-y-0 right-0 rounded-full bg-amber-500" style={{ width: `${staleWidth}%` }} />
        </div>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{item.stale_count} stale in this status</p>
    </div>
  );
}

function InsightMeterCard({
  accentClassName,
  label,
  progress,
  value,
}: {
  accentClassName: string;
  label: string;
  progress: number;
  value: number | string;
}) {
  return (
    <div className="rounded-[1.2rem] border border-border bg-white/80 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200/80">
        <div className={`h-full rounded-full ${accentClassName}`} style={{ width: `${Math.max(progress, 6)}%` }} />
      </div>
    </div>
  );
}

function CampaignFocusSelect({
  campaigns,
  selectedCampaignId,
  onChange,
}: {
  campaigns: DashboardCampaignHealth[];
  selectedCampaignId: number | null;
  onChange: (campaignId: number) => void;
}) {
  return (
    <Select
      className="min-w-[260px]"
      value={selectedCampaignId ? String(selectedCampaignId) : ""}
      onChange={(event) => onChange(Number(event.target.value))}
    >
      {campaigns.map((campaign) => (
        <option key={campaign.campaign_id} value={campaign.campaign_id}>
          {campaign.campaign_name} · {campaign.project_name}
        </option>
      ))}
    </Select>
  );
}

function buildCycleDots(value: number) {
  const visibleDots = Math.min(Math.max(value, 0), 6);
  return Array.from({ length: 6 }, (_, index) => index < visibleDots);
}

function buildProgress(value: number, maxValue: number) {
  if (!maxValue) {
    return 0;
  }
  return Math.min((value / maxValue) * 100, 100);
}

function formatTimelineLabel(value: string) {
  const date = new Date(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
  }).format(date);
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

function buildCampaignBottlenecks(overview: CampaignOverview): DashboardAnalytics["workload"]["bottlenecks_by_status"] {
  const staleCutoff = Date.now() - (3 * 24 * 60 * 60 * 1000);

  return overview.status_breakdown
    .map((stage) => ({
      status: stage.status,
      label: stage.status_label,
      count: stage.count,
      stale_count: overview.drafts.filter(
        (draft) => draft.status === stage.status && new Date(draft.updated_at).getTime() < staleCutoff,
      ).length,
    }))
    .filter((item) => item.count > 0)
    .sort((left, right) => {
      if (right.count !== left.count) {
        return right.count - left.count;
      }
      if (right.stale_count !== left.stale_count) {
        return right.stale_count - left.stale_count;
      }
      return left.label.localeCompare(right.label);
    });
}
