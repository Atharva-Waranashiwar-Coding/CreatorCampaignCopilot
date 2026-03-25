import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select } from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { ContentDraft, DraftStatus } from "../lib/types";

const draftStatuses: DraftStatus[] = [
  "idea",
  "draft",
  "in_review",
  "approved",
  "scheduled",
  "published",
  "rejected",
];

type DraftFormState = {
  title: string;
  platform: string;
  content_type: string;
  content_body: string;
  status: DraftStatus;
  planned_publish_at: string;
};

export function DraftDetailPage() {
  const { draftId } = useParams();
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const [form, setForm] = useState<DraftFormState | null>(null);

  const draftQuery = useQuery({
    queryKey: ["draft", draftId],
    queryFn: () => apiRequest<ContentDraft>(`/drafts/${draftId}`, {}, token),
    enabled: Boolean(draftId),
  });

  useEffect(() => {
    if (!draftQuery.data) {
      return;
    }

    setForm({
      title: draftQuery.data.title,
      platform: draftQuery.data.platform,
      content_type: draftQuery.data.content_type,
      content_body: draftQuery.data.content_body ?? "",
      status: draftQuery.data.status,
      planned_publish_at: toDateTimeLocal(draftQuery.data.planned_publish_at),
    });
  }, [draftQuery.data]);

  const updateMutation = useMutation({
    mutationFn: () =>
      apiRequest<ContentDraft>(`/drafts/${draftId}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: form?.title,
          platform: form?.platform,
          content_type: form?.content_type,
          content_body: form?.content_body || null,
          status: form?.status,
          planned_publish_at: form?.planned_publish_at || null,
        }),
      }, token),
    onSuccess: (draft) => {
      queryClient.invalidateQueries({ queryKey: ["draft", draftId] });
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", String(draft.campaign_id)] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () =>
      apiRequest<void>(`/drafts/${draftId}`, {
        method: "DELETE",
      }, token),
    onSuccess: () => {
      const campaignId = draftQuery.data?.campaign_id;
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      if (campaignId) {
        queryClient.invalidateQueries({ queryKey: ["campaign-overview", String(campaignId)] });
      }
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      navigate(campaignId ? `/campaigns/${campaignId}` : "/drafts");
    },
  });

  const draft = draftQuery.data;

  if (draftQuery.isLoading || !draft || !form) {
    return (
      <Card className="border-white/70 bg-white/85 p-8 shadow-xl shadow-slate-900/5">
        <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Loading draft</p>
      </Card>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Draft Detail"
        title={draft.title}
        description={`${draft.brand_name} · ${draft.project_name} · ${draft.campaign_name}`}
        actions={
          <div className="flex flex-wrap gap-3">
            <Badge tone={draft.status === "in_review" ? "warning" : draft.status === "approved" ? "success" : "muted"}>
              {draft.status.replace(/_/g, " ")}
            </Badge>
            <Link className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" to={`/campaigns/${draft.campaign_id}`}>
              Back to workspace
            </Link>
          </div>
        }
      />

      <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex flex-wrap items-center gap-3">
          <Badge>{draft.platform}</Badge>
          <Badge tone="muted">{draft.content_type}</Badge>
          <p className="text-sm text-muted-foreground">Updated {formatDateTime(draft.updated_at)}</p>
        </div>

        <form
          className="mt-6 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            updateMutation.mutate();
          }}
        >
          <Field label="Title">
            <Input
              value={form.title}
              onChange={(event) => setForm((current) => (current ? { ...current, title: event.target.value } : current))}
            />
          </Field>

          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Platform">
              <Input
                value={form.platform}
                onChange={(event) => setForm((current) => (current ? { ...current, platform: event.target.value } : current))}
              />
            </Field>
            <Field label="Content type">
              <Input
                value={form.content_type}
                onChange={(event) => setForm((current) => (current ? { ...current, content_type: event.target.value } : current))}
              />
            </Field>
            <Field label="Status">
              <Select
                value={form.status}
                onChange={(event) =>
                  setForm((current) => (current ? { ...current, status: event.target.value as DraftStatus } : current))
                }
              >
                {draftStatuses.map((status) => (
                  <option key={status} value={status}>
                    {status.replace(/_/g, " ")}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field label="Planned publish at">
            <Input
              type="datetime-local"
              value={form.planned_publish_at}
              onChange={(event) =>
                setForm((current) => (current ? { ...current, planned_publish_at: event.target.value } : current))
              }
            />
          </Field>

          <Field label="Draft body">
            <Textarea
              className="min-h-[260px]"
              value={form.content_body}
              onChange={(event) =>
                setForm((current) => (current ? { ...current, content_body: event.target.value } : current))
              }
            />
          </Field>

          <MutationFeedback error={updateMutation.error || deleteMutation.error} />

          <div className="flex flex-wrap gap-3">
            <Button disabled={updateMutation.isPending} type="submit">
              {updateMutation.isPending ? "Saving..." : "Save draft"}
            </Button>
            <Button
              disabled={deleteMutation.isPending}
              onClick={() => {
                if (window.confirm(`Delete ${draft.title}?`)) {
                  deleteMutation.mutate();
                }
              }}
              type="button"
              variant="danger"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete draft"}
            </Button>
          </div>
        </form>
      </Card>
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

function toDateTimeLocal(value: string | null) {
  if (!value) {
    return "";
  }

  return value.slice(0, 16);
}
