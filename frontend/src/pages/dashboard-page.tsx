import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { MetricCard } from "../components/shared/metric-card";
import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { useAuthStore } from "../features/auth/auth-store";
import { apiRequest } from "../lib/api";
import { formatDate, formatDateTime } from "../lib/format";
import type {
  Brand,
  DashboardAnalytics,
  DashboardCountBucket,
  DashboardDateBucket,
  DashboardSummary,
} from "../lib/types";

export function DashboardPage() {
  const token = useAuthStore((state) => state.token);
  const [brandFilter, setBrandFilter] = useState("all");

  const brandsQuery = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiRequest<Brand[]>("/brands", {}, token),
  });

  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary", brandFilter],
    queryFn: () => apiRequest<DashboardSummary>(buildDashboardPath("/dashboard/summary", brandFilter), {}, token),
  });

  const analyticsQuery = useQuery({
    queryKey: ["dashboard-analytics", brandFilter],
    queryFn: () =>
      apiRequest<DashboardAnalytics>(buildDashboardPath("/dashboard/analytics", brandFilter), {}, token),
  });

  const summary = summaryQuery.data;
  const analytics = analyticsQuery.data;

  return (
    <div>
      <PageHeader
        eyebrow="Dashboard"
        title="Campaign operations with plan-aware visibility"
        description="Track campaign health, review pressure, scheduled delivery, and workspace usage from a single operational view."
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

      <Card className="mt-8 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Recent activity</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Audit trail basics</h2>
          </div>
          {summaryQuery.isFetching || analyticsQuery.isFetching ? <Badge tone="muted">Refreshing</Badge> : null}
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

function buildDashboardPath(basePath: string, brandFilter: string) {
  if (brandFilter === "all") {
    return basePath;
  }

  const params = new URLSearchParams({ brand_id: brandFilter });
  return `${basePath}?${params.toString()}`;
}
