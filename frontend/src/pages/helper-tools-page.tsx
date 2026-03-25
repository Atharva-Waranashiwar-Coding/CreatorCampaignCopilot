import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatActionLabel, formatDateTime } from "../lib/format";
import type { HelperToolCatalog, ToolUsageLog } from "../lib/types";

export function HelperToolsPage() {
  const token = useAuthStore((state) => state.token);

  const catalogQuery = useQuery({
    queryKey: ["helper-tools", "catalog"],
    queryFn: () => apiRequest<HelperToolCatalog>("/tools/catalog", {}, token),
  });

  const usageQuery = useQuery({
    queryKey: ["helper-tools", "usage"],
    queryFn: () => apiRequest<ToolUsageLog[]>("/tools/usage?limit=20&advanced_only=true", {}, token),
  });

  const catalog = catalogQuery.data;
  const usage = usageQuery.data ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Helper Tools"
        title="Internal MCP helper layer visibility"
        description="Inspect the helper tools exposed through FastAPI, confirm MCP availability, and review recent advanced helper executions across brands you can access."
        actions={(
          <>
            <Badge tone={catalog?.mcp_helpers_enabled ? "success" : "warning"}>
              {catalog?.mcp_helpers_enabled ? "MCP enabled" : "MCP disabled"}
            </Badge>
            <Badge tone={catalog?.mcp_runtime_available ? "success" : "warning"}>
              {catalog?.mcp_runtime_available ? "Runtime available" : "Package missing"}
            </Badge>
          </>
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
                      <Badge tone={tool.mcp_exposed ? "success" : "warning"}>
                        {tool.mcp_exposed ? "MCP exposed" : "REST only"}
                      </Badge>
                      <Badge tone="muted">{tool.target_entity_type}</Badge>
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
