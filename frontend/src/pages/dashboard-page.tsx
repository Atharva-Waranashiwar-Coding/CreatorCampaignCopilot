import { useQuery } from "@tanstack/react-query";

import { MetricCard } from "../components/shared/metric-card";
import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { useAuthStore } from "../features/auth/auth-store";
import { apiRequest } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { DashboardSummary } from "../lib/types";

export function DashboardPage() {
  const token = useAuthStore((state) => state.token);

  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiRequest<DashboardSummary>("/dashboard/summary", {}, token),
  });

  const summary = summaryQuery.data;

  return (
    <div>
      <PageHeader
        eyebrow="Dashboard"
        title="Campaign operations at a glance"
        description="Track the core Phase 1 entities from one workspace shell before briefs, drafts, and reviews are layered on."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          hint="Brands you can access right now."
          label="Brands"
          value={summary?.brand_count ?? 0}
        />
        <MetricCard
          hint="Projects across accessible brands."
          label="Projects"
          value={summary?.project_count ?? 0}
        />
        <MetricCard
          hint="Campaigns currently stored in the workspace."
          label="Campaigns"
          value={summary?.campaign_count ?? 0}
        />
        <MetricCard
          hint="Campaigns actively in motion."
          label="Active campaigns"
          value={summary?.active_campaign_count ?? 0}
        />
      </div>

      <Card className="mt-8 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Recent activity</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Audit trail basics</h2>
          </div>
          {summaryQuery.isFetching ? <Badge tone="muted">Refreshing</Badge> : null}
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
                  <p className="text-sm font-medium text-foreground">{item.action}</p>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {item.actor_name ?? "Unknown user"} · {formatDateTime(item.created_at)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-6 text-sm text-muted-foreground">
            Activity will appear here once brands, projects, campaigns, and membership invites are created.
          </p>
        )}
      </Card>
    </div>
  );
}
