import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Select } from "../components/ui/select";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatActionLabel, formatDate, formatDateTime, formatStatusLabel } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { CampaignOverview, DraftStatus } from "../lib/types";

const draftStatuses: DraftStatus[] = [
  "idea",
  "draft",
  "in_review",
];

type BriefFormState = {
  key_message: string;
  call_to_action: string;
  tone: string;
  channels: string;
  themes: string;
  references: string;
};

type DraftFormState = {
  title: string;
  platform: string;
  content_type: string;
  content_body: string;
  status: DraftStatus;
  planned_publish_at: string;
};

const emptyBriefForm: BriefFormState = {
  key_message: "",
  call_to_action: "",
  tone: "",
  channels: "",
  themes: "",
  references: "",
};

const emptyDraftForm: DraftFormState = {
  title: "",
  platform: "",
  content_type: "",
  content_body: "",
  status: "draft",
  planned_publish_at: "",
};

export function CampaignOverviewPage() {
  const { campaignId } = useParams();
  const token = useAuthStore((state) => state.token);
  const [briefForm, setBriefForm] = useState<BriefFormState>(emptyBriefForm);
  const [draftForm, setDraftForm] = useState<DraftFormState>(emptyDraftForm);

  const overviewQuery = useQuery({
    queryKey: ["campaign-overview", campaignId],
    queryFn: () => apiRequest<CampaignOverview>(`/campaigns/${campaignId}/overview`, {}, token),
    enabled: Boolean(campaignId),
  });

  const overview = overviewQuery.data;
  const campaign = overview?.campaign;

  useEffect(() => {
    if (!overview?.brief) {
      setBriefForm(emptyBriefForm);
      return;
    }

    setBriefForm({
      key_message: overview.brief.key_message ?? "",
      call_to_action: overview.brief.call_to_action ?? "",
      tone: overview.brief.tone ?? "",
      channels: overview.brief.channels.join(", "),
      themes: overview.brief.themes.join(", "),
      references: overview.brief.references ?? "",
    });
  }, [overview?.brief]);

  const createOrUpdateBriefMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/campaigns/${campaignId}/brief`, {
        method: "PUT",
        body: JSON.stringify({
          ...briefForm,
          channels: splitList(briefForm.channels),
          themes: splitList(briefForm.themes),
        }),
      }, token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const deleteBriefMutation = useMutation({
    mutationFn: () =>
      apiRequest<void>(`/campaigns/${campaignId}/brief`, {
        method: "DELETE",
      }, token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });

  const createDraftMutation = useMutation({
    mutationFn: () =>
      apiRequest("/drafts", {
        method: "POST",
        body: JSON.stringify({
          campaign_id: Number(campaignId),
          title: draftForm.title,
          platform: draftForm.platform,
          content_type: draftForm.content_type,
          content_body: draftForm.content_body || null,
          status: draftForm.status,
          planned_publish_at: draftForm.planned_publish_at || null,
        }),
      }, token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      setDraftForm(emptyDraftForm);
    },
  });

  const draftTotal = useMemo(() => overview?.drafts.length ?? 0, [overview?.drafts.length]);

  if (overviewQuery.isLoading) {
    return <LoadingState label="Loading campaign workspace" />;
  }

  if (!campaign || !overview) {
    return <LoadingState label="Campaign not found" />;
  }

  return (
    <div>
      <PageHeader
        eyebrow="Campaign Workspace"
        title={campaign.name}
        description={`${campaign.brand_name} · ${campaign.project_name} · ${formatDate(campaign.start_date)} to ${formatDate(campaign.end_date)}`}
        actions={
          <div className="flex flex-wrap gap-3">
            <Badge tone={campaign.status === "active" ? "success" : "muted"}>{campaign.status}</Badge>
            <Link className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" to="/campaigns">
              Back to campaigns
            </Link>
          </div>
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Drafts" value={draftTotal} />
        <MetricCard label="Brief" value={overview.brief ? "Ready" : "Missing"} />
        <MetricCard label="Objective" value={campaign.objective ?? "Not set"} />
        <MetricCard label="Audience" value={campaign.audience ?? "Not set"} />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Content brief</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign brief</h2>
            </div>
            {overview.brief ? <Badge tone="success">Saved</Badge> : <Badge tone="warning">Draft</Badge>}
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              createOrUpdateBriefMutation.mutate();
            }}
          >
            <Field label="Key message">
              <Textarea
                value={briefForm.key_message}
                onChange={(event) => setBriefForm((current) => ({ ...current, key_message: event.target.value }))}
              />
            </Field>
            <Field label="Call to action">
              <Input
                value={briefForm.call_to_action}
                onChange={(event) => setBriefForm((current) => ({ ...current, call_to_action: event.target.value }))}
              />
            </Field>
            <Field label="Tone">
              <Input
                value={briefForm.tone}
                onChange={(event) => setBriefForm((current) => ({ ...current, tone: event.target.value }))}
              />
            </Field>
            <Field label="Channels">
              <Input
                placeholder="LinkedIn, Instagram, Email"
                value={briefForm.channels}
                onChange={(event) => setBriefForm((current) => ({ ...current, channels: event.target.value }))}
              />
            </Field>
            <Field label="Themes">
              <Input
                placeholder="Launch, trust, creator proof"
                value={briefForm.themes}
                onChange={(event) => setBriefForm((current) => ({ ...current, themes: event.target.value }))}
              />
            </Field>
            <Field label="References">
              <Textarea
                value={briefForm.references}
                onChange={(event) => setBriefForm((current) => ({ ...current, references: event.target.value }))}
              />
            </Field>

            <MutationFeedback error={createOrUpdateBriefMutation.error || deleteBriefMutation.error} />
            <div className="flex flex-wrap gap-3">
              <Button disabled={createOrUpdateBriefMutation.isPending} type="submit">
                {createOrUpdateBriefMutation.isPending ? "Saving..." : "Save brief"}
              </Button>
              {overview.brief ? (
                <Button
                  disabled={deleteBriefMutation.isPending}
                  onClick={() => deleteBriefMutation.mutate()}
                  type="button"
                  variant="ghost"
                >
                  {deleteBriefMutation.isPending ? "Removing..." : "Remove brief"}
                </Button>
              ) : null}
            </div>
          </form>
        </Card>

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Draft pipeline</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Status breakdown</h2>
              </div>
              <Link className="text-sm font-medium text-primary" to="/drafts">
                Open all drafts
              </Link>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {overview.status_breakdown.map((item) => (
                <div key={item.status} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{formatStatusLabel(item.status)}</p>
                  <p className="mt-3 text-3xl font-semibold tracking-tight">{item.count}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">New draft</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Create working copy</h2>
            </div>

            <form
              className="mt-5 space-y-4"
              onSubmit={(event) => {
                event.preventDefault();
                createDraftMutation.mutate();
              }}
            >
              <Field label="Title">
                <Input
                  value={draftForm.title}
                  onChange={(event) => setDraftForm((current) => ({ ...current, title: event.target.value }))}
                />
              </Field>
              <div className="grid gap-4 md:grid-cols-3">
                <Field label="Platform">
                  <Input
                    value={draftForm.platform}
                    onChange={(event) => setDraftForm((current) => ({ ...current, platform: event.target.value }))}
                  />
                </Field>
                <Field label="Content type">
                  <Input
                    value={draftForm.content_type}
                    onChange={(event) => setDraftForm((current) => ({ ...current, content_type: event.target.value }))}
                  />
                </Field>
                <Field label="Status">
                  <Select
                    value={draftForm.status}
                    onChange={(event) => setDraftForm((current) => ({ ...current, status: event.target.value as DraftStatus }))}
                  >
                    {draftStatuses.map((status) => (
                      <option key={status} value={status}>
                        {formatStatusLabel(status)}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              <Field label="Planned publish at">
                <Input
                  type="datetime-local"
                  value={draftForm.planned_publish_at}
                  onChange={(event) =>
                    setDraftForm((current) => ({ ...current, planned_publish_at: event.target.value }))
                  }
                />
              </Field>
              <Field label="Draft body">
                <Textarea
                  className="min-h-[180px]"
                  value={draftForm.content_body}
                  onChange={(event) => setDraftForm((current) => ({ ...current, content_body: event.target.value }))}
                />
              </Field>

              <MutationFeedback error={createDraftMutation.error} />
              <Button disabled={createDraftMutation.isPending} type="submit">
                {createDraftMutation.isPending ? "Creating..." : "Create draft"}
              </Button>
            </form>
          </Card>
        </div>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Drafts</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign working set</h2>
            </div>
            <Badge tone="muted">{overview.drafts.length} total</Badge>
          </div>

          <div className="mt-5 space-y-3">
            {overview.drafts.length ? (
              overview.drafts.map((draft) => (
                <Link
                  key={draft.id}
                  className="block rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 transition hover:bg-white"
                  to={`/drafts/${draft.id}`}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-base font-semibold">{draft.title}</h3>
                    <Badge>{draft.platform}</Badge>
                    <Badge tone={draft.status === "in_review" ? "warning" : draft.status === "approved" ? "success" : "muted"}>
                      {formatStatusLabel(draft.status)}
                    </Badge>
                    <Badge tone="muted">{draft.review_count} reviews</Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{draft.content_type}</p>
                  {draft.latest_review_action ? (
                    <p className="mt-3 text-sm text-muted-foreground">
                      Latest review: {formatActionLabel(draft.latest_review_action)} · {formatDateTime(draft.latest_reviewed_at)}
                    </p>
                  ) : null}
                  <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    Updated {formatDateTime(draft.updated_at)}
                  </p>
                </Link>
              ))
            ) : (
              <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                No drafts yet. Create the first working draft for this campaign above.
              </p>
            )}
          </div>
        </Card>

        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Campaign activity</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Timeline</h2>
            </div>
            <Badge tone="muted">{overview.activity_timeline.length} events</Badge>
          </div>

          <div className="mt-5 space-y-3">
            {overview.activity_timeline.length ? (
              overview.activity_timeline.map((item) => (
                <div key={item.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge>{item.entity_type}</Badge>
                    <p className="text-sm font-medium text-foreground">{formatActionLabel(item.action)}</p>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {item.actor_name ?? "Unknown user"} · {formatDateTime(item.created_at)}
                  </p>
                  {"version_number" in item.metadata ? (
                    <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      Version {String(item.metadata.version_number)}
                    </p>
                  ) : null}
                </div>
              ))
            ) : (
              <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                Campaign activity will appear here once drafts begin moving through review.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Field({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{label}</p>
      <p className="mt-4 text-2xl font-semibold tracking-tight">{value}</p>
    </Card>
  );
}

function MutationFeedback({ error }: { error: unknown }) {
  if (!error) {
    return null;
  }

  return (
    <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error instanceof ApiError ? error.message : "Request failed."}
    </p>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <Card className="border-white/70 bg-white/85 p-8 shadow-xl shadow-slate-900/5">
      <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">{label}</p>
    </Card>
  );
}

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}
