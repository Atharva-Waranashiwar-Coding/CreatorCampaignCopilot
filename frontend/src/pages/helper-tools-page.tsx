import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { Select } from "../components/ui/select";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatActionLabel, formatDateTime } from "../lib/format";
import type { Brand, BrandBillingSnapshot, HelperToolCatalog, ToolUsageLog, UsageMetric } from "../lib/types";

export function HelperToolsPage() {
  const token = useAuthStore((state) => state.token);
  const [selectedBrandId, setSelectedBrandId] = useState<number | null>(null);

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

  const catalogQuery = useQuery({
    queryKey: ["helper-tools", "catalog"],
    queryFn: () => apiRequest<HelperToolCatalog>("/tools/catalog", {}, token),
  });

  const billingQuery = useQuery({
    queryKey: ["brand-billing", selectedBrandId],
    queryFn: () => apiRequest<BrandBillingSnapshot>(`/brands/${selectedBrandId}/billing`, {}, token),
    enabled: Boolean(selectedBrandId),
  });

  const usageQuery = useQuery({
    queryKey: ["helper-tools", "usage"],
    queryFn: () => apiRequest<ToolUsageLog[]>("/tools/usage?limit=20&advanced_only=true", {}, token),
  });

  const catalog = catalogQuery.data;
  const billingSnapshot = billingQuery.data;
  const usage = usageQuery.data ?? [];
  const helperUsage = (billingSnapshot?.usage ?? []).filter((metric) =>
    ["monthly_helper_runs", "monthly_advanced_helper_runs", "saved_helper_artifacts"].includes(metric.key),
  );

  return (
    <div>
      <PageHeader
        eyebrow="Helper Tools"
        title="Internal MCP helper layer visibility"
        description="Inspect the helper tools exposed through FastAPI, confirm MCP availability, and review recent advanced helper executions across brands you can access."
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
            <Badge tone={catalog?.mcp_helpers_enabled ? "success" : "warning"}>
              {catalog?.mcp_helpers_enabled ? "MCP enabled" : "MCP disabled"}
            </Badge>
            <Badge tone={catalog?.mcp_runtime_available ? "success" : "warning"}>
              {catalog?.mcp_runtime_available ? "Runtime available" : "Package missing"}
            </Badge>
          </div>
        )}
      />

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Catalog</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Available helper tools</h2>
              </div>
              {catalog ? <Badge tone="muted">{catalog.tools.length} tools</Badge> : null}
            </div>

            <CatalogStatus catalog={catalog} isLoading={catalogQuery.isLoading} />
            <QueryError error={catalogQuery.error} />

            {catalog?.tools.length ? (
              <div className="mt-6 grid gap-4">
                {catalog.tools.map((tool) => (
                  <div
                    key={tool.name}
                    className="rounded-[1.5rem] border border-border bg-white/80 p-5"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge>{tool.mcp_tool_name}</Badge>
                      <Badge tone={tool.is_advanced ? "warning" : "muted"}>
                        {tool.is_advanced ? "Advanced AI" : "Core helper"}
                      </Badge>
                      <Badge tone={tool.mcp_exposed ? "success" : "warning"}>
                        {tool.mcp_exposed ? "MCP exposed" : "REST only"}
                      </Badge>
                      <Badge tone="muted">{tool.target_entity_type}</Badge>
                      <Badge tone="muted">{tool.required_feature_key}</Badge>
                    </div>
                    <p className="mt-4 text-sm leading-6 text-muted-foreground">{tool.description}</p>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div className="rounded-[1.25rem] border border-border bg-slate-50/90 p-4">
                        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">REST route</p>
                        <p className="mt-2 text-sm font-medium text-foreground">
                          {tool.http_method} {tool.rest_path}
                        </p>
                      </div>
                      <div className="rounded-[1.25rem] border border-border bg-slate-50/90 p-4">
                        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Service bindings</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {tool.service_bindings.map((binding) => (
                            <Badge key={binding} tone="muted">
                              {binding}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Plan gating</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Helper access and burst controls</h2>
              </div>
              {billingSnapshot ? <Badge tone="muted">{billingSnapshot.current_plan.name}</Badge> : null}
            </div>

            <QueryError error={brandsQuery.error} />
            <QueryError error={billingQuery.error} />

            {billingQuery.isLoading ? (
              <p className="mt-6 text-sm text-muted-foreground">Loading helper access policy...</p>
            ) : billingSnapshot ? (
              <div className="mt-6 space-y-4">
                <div className="flex flex-wrap gap-3">
                  <Badge tone={billingSnapshot.helper_policy.helper_tools_enabled ? "success" : "warning"}>
                    {billingSnapshot.helper_policy.helper_tools_enabled ? "Helper tools enabled" : "Helper tools locked"}
                  </Badge>
                  <Badge tone={billingSnapshot.helper_policy.advanced_ai_helpers_enabled ? "success" : "warning"}>
                    {billingSnapshot.helper_policy.advanced_ai_helpers_enabled ? "Advanced AI enabled" : "Advanced AI locked"}
                  </Badge>
                  <Badge tone="muted">{billingSnapshot.current_user_role}</Badge>
                </div>

                <div className="grid gap-4">
                  <PolicyBlock
                    label="Monthly allowances"
                    lines={helperUsage.length
                      ? helperUsage.map((metric) => formatHelperMetric(metric))
                      : ["No helper usage meters are available for this brand yet."]}
                  />
                  <PolicyBlock
                    label="Burst throttles"
                    lines={[
                      formatBurstPolicy(
                        "All helper runs",
                        billingSnapshot.helper_policy.helper_run_burst_limit,
                        billingSnapshot.helper_policy.helper_run_burst_window_minutes,
                      ),
                      formatBurstPolicy(
                        "Advanced AI helper runs",
                        billingSnapshot.helper_policy.advanced_helper_run_burst_limit,
                        billingSnapshot.helper_policy.advanced_helper_run_burst_window_minutes,
                      ),
                    ]}
                  />
                </div>

                {billingSnapshot.upgrade_prompts.length ? (
                  <div className="space-y-2 rounded-[1.25rem] border border-amber-200 bg-amber-50 p-4">
                    {billingSnapshot.upgrade_prompts.slice(0, 2).map((prompt) => (
                      <p key={prompt} className="text-sm text-amber-900">
                        {prompt}
                      </p>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Usage</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Recent advanced executions</h2>
              </div>
              {usage.length ? <Badge tone="muted">{usage.length} entries</Badge> : null}
            </div>

            <QueryError error={usageQuery.error} />

            {usageQuery.isLoading ? (
              <p className="mt-6 text-sm text-muted-foreground">Loading helper tool activity...</p>
            ) : usage.length ? (
              <div className="mt-6 space-y-3">
                {usage.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-[1.4rem] border border-border bg-white/80 p-4"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge>{item.tool_name}</Badge>
                      <Badge tone={item.was_successful ? "success" : "warning"}>
                        {item.was_successful ? "Success" : "Failed"}
                      </Badge>
                      <Badge tone="muted">{item.invocation_source}</Badge>
                    </div>
                    <p className="mt-3 text-sm text-foreground">
                      {item.actor_name ?? "Unknown user"} on {item.brand_name ?? "cross-brand context"} ·{" "}
                      {formatDateTime(item.created_at)}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      Target: {formatActionLabel(item.target_entity_type)}{" "}
                      {item.target_entity_id ? `#${item.target_entity_id}` : "context"}
                    </p>
                    {item.draft_id || item.campaign_id ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.draft_id ? <Badge tone="muted">Draft #{item.draft_id}</Badge> : null}
                        {item.campaign_id ? <Badge tone="muted">Campaign #{item.campaign_id}</Badge> : null}
                      </div>
                    ) : null}
                    <p className="mt-3 text-sm text-muted-foreground">{extractUsageSummary(item)}</p>
                    <div className="mt-4 grid gap-3">
                      <PayloadBlock label="Request trace" value={item.request_trace ?? item.request_payload} />
                      <PayloadBlock
                        label={item.was_successful ? "Result trace" : "Error trace"}
                        value={item.was_successful ? item.result_trace ?? item.result_summary : { error: item.error_detail }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-6 text-sm text-muted-foreground">
                Advanced helper activity will appear here once tone validation, adaptation, recommendation, or revision-conversion tools are exercised.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function PolicyBlock({
  label,
  lines,
}: {
  label: string;
  lines: string[];
}) {
  return (
    <div className="rounded-[1.25rem] border border-border bg-slate-50/90 p-4">
      <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{label}</p>
      <div className="mt-3 space-y-2">
        {lines.map((line) => (
          <p key={line} className="text-sm text-foreground">
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}

function CatalogStatus({
  catalog,
  isLoading,
}: {
  catalog: HelperToolCatalog | undefined;
  isLoading: boolean;
}) {
  if (isLoading) {
    return <p className="mt-6 text-sm text-muted-foreground">Loading helper tool catalog...</p>;
  }

  if (!catalog) {
    return null;
  }

  return (
    <div className="mt-6 grid gap-4 md:grid-cols-2">
      <div className="rounded-[1.35rem] border border-border bg-slate-50/90 p-4">
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">MCP mount</p>
        <p className="mt-2 text-sm font-medium text-foreground">{catalog.mcp_mount_path ?? "Disabled"}</p>
      </div>
      <div className="rounded-[1.35rem] border border-border bg-slate-50/90 p-4">
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Transport</p>
        <p className="mt-2 text-sm font-medium text-foreground">
          {catalog.mcp_http_transport_enabled ? "HTTP" : "HTTP off"}
          {catalog.mcp_sse_transport_enabled ? " + SSE" : ""}
        </p>
      </div>
    </div>
  );
}

function PayloadBlock({
  label,
  value,
}: {
  label: string;
  value: Record<string, unknown> | null;
}) {
  const text = truncateJson(value);

  return (
    <div className="rounded-[1.1rem] border border-border bg-slate-50/80 p-3">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs leading-5 text-slate-700">
        {text}
      </pre>
    </div>
  );
}

function QueryError({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      {error.message}
    </p>
  );
}

function truncateJson(value: Record<string, unknown> | null | undefined) {
  const text = JSON.stringify(value ?? {}, null, 2);
  if (text.length <= 600) {
    return text;
  }
  return `${text.slice(0, 597).trimEnd()}...`;
}

function formatHelperMetric(metric: UsageMetric) {
  if (metric.limit === null) {
    return `${metric.label}: ${metric.current} used with no monthly cap.`;
  }
  return `${metric.label}: ${metric.current}/${metric.limit} used, ${metric.remaining ?? 0} remaining.`;
}

function formatBurstPolicy(label: string, limit: number | null, windowMinutes: number) {
  if (limit === null) {
    return `${label}: no burst cap in the current ${windowMinutes}-minute window.`;
  }
  return `${label}: ${limit} allowed every ${windowMinutes} minutes.`;
}

function extractUsageSummary(item: ToolUsageLog) {
  const summary = item.result_trace?.summary;
  if (typeof summary === "string" && summary.trim()) {
    return summary;
  }
  if (!item.was_successful && item.error_detail) {
    return item.error_detail;
  }
  return "Structured request and result traces are available below.";
}
