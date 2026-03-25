import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatDate, formatDateTime } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type {
  Brand,
  BrandBillingSnapshot,
  FeatureAccess,
  Plan,
  PlanInterval,
  UsageMetric,
} from "../lib/types";

export function BillingPage() {
  const token = useAuthStore((state) => state.token);
  const [selectedBrandId, setSelectedBrandId] = useState<number | null>(null);
  const [billingInterval, setBillingInterval] = useState<PlanInterval>("monthly");

  const brandsQuery = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiRequest<Brand[]>("/brands", {}, token),
  });

  useEffect(() => {
    if (!brandsQuery.data?.length) {
      setSelectedBrandId(null);
      return;
    }

    if (!selectedBrandId || !brandsQuery.data.some((brand) => brand.id === selectedBrandId)) {
      setSelectedBrandId(brandsQuery.data[0].id);
    }
  }, [brandsQuery.data, selectedBrandId]);

  const billingQuery = useQuery({
    queryKey: ["brand-billing", selectedBrandId],
    queryFn: () => apiRequest<BrandBillingSnapshot>(`/brands/${selectedBrandId}/billing`, {}, token),
    enabled: Boolean(selectedBrandId),
  });

  useEffect(() => {
    if (billingQuery.data?.subscription.billing_interval) {
      setBillingInterval(billingQuery.data.subscription.billing_interval);
    }
  }, [billingQuery.data?.subscription.billing_interval]);

  const planMutation = useMutation({
    mutationFn: (planCode: string) =>
      apiRequest<BrandBillingSnapshot>(
        `/brands/${selectedBrandId}/subscription`,
        {
          method: "PATCH",
          body: JSON.stringify({
            plan_code: planCode,
            billing_interval: billingInterval,
          }),
        },
        token,
      ),
    onSuccess: () => {
      if (selectedBrandId) {
        queryClient.invalidateQueries({ queryKey: ["brand-billing", selectedBrandId] });
      }
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const snapshot = billingQuery.data;
  const canManagePlan = snapshot?.current_user_role === "owner" || snapshot?.current_user_role === "admin";

  return (
    <div>
      <PageHeader
        eyebrow="Billing"
        title="Plan, usage, and upgrade controls"
        description="Inspect the current subscription, monitor brand-level usage against plan limits, and change plans without leaving the workspace."
        actions={(
          <div className="flex flex-wrap gap-3">
            <Select
              className="min-w-[220px]"
              value={selectedBrandId ? String(selectedBrandId) : ""}
              onChange={(event) => setSelectedBrandId(Number(event.target.value))}
            >
              {brandsQuery.data?.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </Select>
            <Select
              className="min-w-[160px]"
              value={billingInterval}
              onChange={(event) => setBillingInterval(event.target.value as PlanInterval)}
            >
              <option value="monthly">Monthly billing</option>
              <option value="yearly">Yearly billing</option>
            </Select>
          </div>
        )}
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Current plan</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">
                {snapshot?.current_plan.name ?? "Loading..."}
              </h2>
            </div>
            {snapshot ? <Badge>{snapshot.current_user_role}</Badge> : null}
          </div>

          {billingQuery.isLoading ? (
            <p className="mt-6 text-sm text-muted-foreground">Loading billing state...</p>
          ) : snapshot ? (
            <div className="mt-6 space-y-5">
              <div className="rounded-[1.5rem] border border-border bg-white/80 p-5">
                <p className="text-sm text-muted-foreground">
                  {snapshot.current_plan.description ?? "No plan description available."}
                </p>
                <p className="mt-4 text-4xl font-semibold tracking-tight">
                  {formatPlanPrice(snapshot.current_plan, billingInterval)}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Status: <span className="font-medium capitalize text-foreground">{snapshot.subscription.status.replace(/_/g, " ")}</span>
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Current period ends {formatDate(snapshot.subscription.current_period_end)}
                </p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-lg font-semibold tracking-tight">Upgrade prompts</h3>
                  {planMutation.isPending ? <Badge tone="muted">Updating</Badge> : null}
                </div>
                {snapshot.upgrade_prompts.length ? (
                  snapshot.upgrade_prompts.map((prompt) => (
                    <div
                      key={prompt}
                      className="rounded-[1.25rem] border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900"
                    >
                      {prompt}
                    </div>
                  ))
                ) : (
                  <p className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 text-sm text-muted-foreground">
                    No upgrade pressure right now. Current capacity is healthy.
                  </p>
                )}
              </div>

              <div className="space-y-3">
                <h3 className="text-lg font-semibold tracking-tight">Recent plan activity</h3>
                {snapshot.recent_plan_activity.length ? (
                  snapshot.recent_plan_activity.map((item) => (
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
                  ))
                ) : (
                  <p className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 text-sm text-muted-foreground">
                    Plan changes will be logged here as the subscription state changes.
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </Card>

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Usage</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Live plan consumption</h2>
              </div>
              {snapshot ? <Badge tone="muted">{snapshot.usage.length} meters</Badge> : null}
            </div>

            {billingQuery.isLoading ? (
              <p className="mt-6 text-sm text-muted-foreground">Loading usage metrics...</p>
            ) : (
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                {snapshot?.usage.map((metric) => (
                  <UsageMeterCard key={metric.key} metric={metric} />
                ))}
              </div>
            )}
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Features</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">What the plan unlocks</h2>
              </div>
            </div>

            {billingQuery.isLoading ? (
              <p className="mt-6 text-sm text-muted-foreground">Loading feature access...</p>
            ) : (
              <div className="mt-6 space-y-3">
                {snapshot?.features.map((feature) => (
                  <FeatureRow key={feature.key} feature={feature} />
                ))}
              </div>
            )}
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Plans</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Upgrade or rebalance capacity</h2>
              </div>
              {!canManagePlan && snapshot ? <Badge tone="warning">Read only</Badge> : null}
            </div>

            <div className="mt-6 grid gap-4 xl:grid-cols-3">
              {snapshot?.available_plans.map((plan) => (
                <PlanCard
                  key={plan.code}
                  billingInterval={billingInterval}
                  canManagePlan={Boolean(canManagePlan)}
                  currentPlanCode={snapshot.current_plan.code}
                  onSelect={(planCode) => planMutation.mutate(planCode)}
                  plan={plan}
                  saving={planMutation.isPending}
                />
              ))}
            </div>

            <div className="mt-5">
              <MutationFeedback error={planMutation.error} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function UsageMeterCard({ metric }: { metric: UsageMetric }) {
  const width = metric.percent_used ?? 8;
  const barTone =
    metric.status === "at_limit"
      ? "bg-[linear-gradient(90deg,rgba(190,24,93,0.92),rgba(244,63,94,0.82))]"
      : metric.status === "warning"
        ? "bg-[linear-gradient(90deg,rgba(191,87,0,0.9),rgba(245,158,11,0.82))]"
        : "bg-[linear-gradient(90deg,rgba(12,86,102,0.96),rgba(26,132,153,0.82))]";

  return (
    <div className="rounded-[1.25rem] border border-border bg-white/80 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-foreground">{metric.label}</p>
        <Badge tone={metric.status === "at_limit" ? "warning" : metric.status === "warning" ? "warning" : "muted"}>
          {metric.limit === null ? "Unlimited" : `${metric.current}/${metric.limit}`}
        </Badge>
      </div>
      <div className="mt-4 h-2 rounded-full bg-slate-200/80">
        <div
          className={`h-full rounded-full ${barTone}`}
          style={{ width: `${metric.limit === null ? 100 : Math.max(width, metric.current ? 8 : 0)}%` }}
        />
      </div>
      <p className="mt-3 text-sm text-muted-foreground">
        {metric.limit === null
          ? `${metric.current} currently in use with no hard plan cap.`
          : `${metric.remaining ?? 0} remaining before the current limit is reached.`}
      </p>
    </div>
  );
}

function FeatureRow({ feature }: { feature: FeatureAccess }) {
  return (
    <div className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">{feature.label}</p>
          <p className="mt-1 text-sm text-muted-foreground">{feature.description}</p>
        </div>
        <Badge tone={feature.enabled ? "success" : "warning"}>
          {feature.enabled ? "Enabled" : "Locked"}
        </Badge>
      </div>
    </div>
  );
}

function PlanCard({
  billingInterval,
  canManagePlan,
  currentPlanCode,
  onSelect,
  plan,
  saving,
}: {
  billingInterval: PlanInterval;
  canManagePlan: boolean;
  currentPlanCode: string;
  onSelect: (planCode: string) => void;
  plan: Plan;
  saving: boolean;
}) {
  const isCurrent = currentPlanCode === plan.code;

  return (
    <div
      className={[
        "rounded-[1.5rem] border p-5 transition",
        isCurrent ? "border-primary bg-primary/5" : "border-border bg-white/80",
      ].join(" ")}
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xl font-semibold tracking-tight">{plan.name}</h3>
        {isCurrent ? <Badge>Current</Badge> : null}
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{plan.description ?? "No description available."}</p>
      <p className="mt-5 text-4xl font-semibold tracking-tight">{formatPlanPrice(plan, billingInterval)}</p>
      <div className="mt-5 space-y-2 text-sm text-muted-foreground">
        <p>{formatLimitText(plan, "max_templates", "templates")}</p>
        <p>{formatLimitText(plan, "max_active_campaigns", "active campaigns")}</p>
        <p>{formatLimitText(plan, "max_members", "members")}</p>
      </div>
      <Button
        className="mt-6 w-full"
        disabled={saving || !canManagePlan || isCurrent}
        onClick={() => onSelect(plan.code)}
        variant={isCurrent ? "secondary" : "primary"}
      >
        {isCurrent ? "Current plan" : saving ? "Updating..." : `Switch to ${plan.name}`}
      </Button>
    </div>
  );
}

function MutationFeedback({ error }: { error: Error | null }) {
  if (!error) {
    return null;
  }

  return (
    <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error instanceof ApiError ? error.message : "Something went wrong. Please try again."}
    </p>
  );
}

function formatPlanPrice(plan: Plan, interval: PlanInterval) {
  const cents = interval === "yearly" ? (plan.yearly_price_cents ?? plan.monthly_price_cents) : plan.monthly_price_cents;
  if (cents === 0) {
    return "Free";
  }

  return `${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100)}/${interval === "yearly" ? "yr" : "mo"}`;
}

function formatLimitText(plan: Plan, key: string, label: string) {
  const value = plan.limits[key];
  return value === null ? `Unlimited ${label}` : `${value} ${label}`;
}
