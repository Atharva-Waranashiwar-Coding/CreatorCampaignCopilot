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
import { Textarea } from "../components/ui/textarea";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatActionLabel, formatDateTime, formatStatusLabel } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { ContentDraft, DraftReviewAction, DraftReviewThread } from "../lib/types";

type DraftFormState = {
  title: string;
  platform: string;
  content_type: string;
  content_body: string;
  planned_publish_at: string;
};

type WorkflowMutationInput = {
  action: DraftReviewAction;
  body: Record<string, unknown>;
  path: string;
};

export function DraftDetailPage() {
  const { draftId } = useParams();
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const [form, setForm] = useState<DraftFormState | null>(null);
  const [reviewNote, setReviewNote] = useState("");

  const draftQuery = useQuery({
    queryKey: ["draft", draftId],
    queryFn: () => apiRequest<ContentDraft>(`/drafts/${draftId}`, {}, token),
    enabled: Boolean(draftId),
  });

  const reviewThreadQuery = useQuery({
    queryKey: ["draft-reviews", draftId],
    queryFn: () => apiRequest<DraftReviewThread>(`/drafts/${draftId}/reviews`, {}, token),
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
          planned_publish_at: form?.planned_publish_at || null,
        }),
      }, token),
    onSuccess: (draft) => {
      invalidateDraftQueries(draft.campaign_id, String(draft.id));
    },
  });

  const workflowMutation = useMutation({
    mutationFn: ({ body, path }: WorkflowMutationInput) =>
      apiRequest(path, {
        method: "POST",
        body: JSON.stringify(body),
      }, token),
    onSuccess: async () => {
      const campaignId = draftQuery.data?.campaign_id;
      await invalidateDraftQueries(campaignId, draftId);
      setReviewNote("");
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
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      if (campaignId) {
        queryClient.invalidateQueries({ queryKey: ["campaign-overview", String(campaignId)] });
      }
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      navigate(campaignId ? `/campaigns/${campaignId}` : "/drafts");
    },
  });

  const draft = draftQuery.data;
  const reviewThread = reviewThreadQuery.data;
  const availableActions = reviewThread?.available_actions ?? [];

  if (draftQuery.isLoading || reviewThreadQuery.isLoading || !draft || !form || !reviewThread) {
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
            <Badge tone={statusTone(draft.status)}>{formatStatusLabel(draft.status)}</Badge>
            <Badge tone="muted">v{draft.current_version_number}</Badge>
            <Link
              className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              to={`/campaigns/${draft.campaign_id}`}
            >
              Back to workspace
            </Link>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-wrap items-center gap-3">
            <Badge>{draft.platform}</Badge>
            <Badge tone="muted">{draft.content_type}</Badge>
            <Badge tone="muted">{reviewThread.current_user_role}</Badge>
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

            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Platform">
                <Input
                  value={form.platform}
                  onChange={(event) => setForm((current) => (current ? { ...current, platform: event.target.value } : current))}
                />
              </Field>
              <Field label="Content type">
                <Input
                  value={form.content_type}
                  onChange={(event) =>
                    setForm((current) => (current ? { ...current, content_type: event.target.value } : current))
                  }
                />
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

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Review workflow</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Feedback and decisions</h2>
              </div>
              <Badge tone={availableActions.length ? "warning" : "muted"}>
                {availableActions.length ? "Actions available" : "Read only"}
              </Badge>
            </div>

            <div className="mt-5 rounded-[1.25rem] border border-border bg-white/80 p-4">
              <p className="text-sm text-muted-foreground">
                Reviewer notes, approvals, rejections, and editor resubmissions all flow through explicit actions here.
              </p>
            </div>

            <div className="mt-5 space-y-3">
              <Field label="Review note">
                <Textarea
                  className="min-h-[140px]"
                  placeholder="Add reviewer feedback or editor resubmission context"
                  value={reviewNote}
                  onChange={(event) => setReviewNote(event.target.value)}
                />
              </Field>

              <MutationFeedback error={workflowMutation.error} />

              <div className="flex flex-wrap gap-3">
                {availableActions.includes("commented") ? (
                  <Button
                    disabled={workflowMutation.isPending || !reviewNote.trim()}
                    onClick={() =>
                      workflowMutation.mutate({
                        action: "commented",
                        path: `/drafts/${draft.id}/reviews`,
                        body: { comment: reviewNote },
                      })
                    }
                    variant="secondary"
                  >
                    Add note
                  </Button>
                ) : null}
                {availableActions.includes("submitted") ? (
                  <Button
                    disabled={workflowMutation.isPending}
                    onClick={() =>
                      workflowMutation.mutate({
                        action: "submitted",
                        path: `/drafts/${draft.id}/submit`,
                        body: { comment: reviewNote || null },
                      })
                    }
                  >
                    Submit for review
                  </Button>
                ) : null}
                {availableActions.includes("approved") ? (
                  <Button
                    className="bg-emerald-600 text-white hover:bg-emerald-700"
                    disabled={workflowMutation.isPending}
                    onClick={() =>
                      workflowMutation.mutate({
                        action: "approved",
                        path: `/drafts/${draft.id}/approve`,
                        body: { comment: reviewNote || null },
                      })
                    }
                  >
                    Approve
                  </Button>
                ) : null}
                {availableActions.includes("rejected") ? (
                  <Button
                    disabled={workflowMutation.isPending || !reviewNote.trim()}
                    onClick={() =>
                      workflowMutation.mutate({
                        action: "rejected",
                        path: `/drafts/${draft.id}/reject`,
                        body: { comment: reviewNote || null },
                      })
                    }
                    variant="danger"
                  >
                    Reject
                  </Button>
                ) : null}
                {availableActions.includes("resubmitted") ? (
                  <Button
                    disabled={workflowMutation.isPending}
                    onClick={() =>
                      workflowMutation.mutate({
                        action: "resubmitted",
                        path: `/drafts/${draft.id}/resubmit`,
                        body: { comment: reviewNote || null },
                      })
                    }
                  >
                    Resubmit
                  </Button>
                ) : null}
              </div>
            </div>
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Review history</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Revision loop</h2>
              </div>
              <Badge tone="muted">{reviewThread.reviews.length} events</Badge>
            </div>

            <div className="mt-5 space-y-3">
              {reviewThread.reviews.length ? (
                reviewThread.reviews.map((review) => (
                  <div key={review.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge tone={reviewTone(review.action)}>{formatActionLabel(review.action)}</Badge>
                      <Badge tone="muted">v{review.version_number}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {review.actor_name ?? "Unknown user"} · {formatDateTime(review.created_at)}
                    </p>
                    {review.comment ? <p className="mt-3 text-sm leading-6 text-foreground">{review.comment}</p> : null}
                    {review.from_status || review.to_status ? (
                      <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        {formatStatusLabel(review.from_status ?? "unknown")} to {formatStatusLabel(review.to_status ?? "unknown")}
                      </p>
                    ) : null}
                  </div>
                ))
              ) : (
                <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  Review history will appear here once the draft enters feedback.
                </p>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

async function invalidateDraftQueries(campaignId: number | undefined, draftId: string | undefined) {
  if (draftId) {
    await queryClient.invalidateQueries({ queryKey: ["draft", draftId] });
    await queryClient.invalidateQueries({ queryKey: ["draft-reviews", draftId] });
  }
  await queryClient.invalidateQueries({ queryKey: ["drafts"] });
  await queryClient.invalidateQueries({ queryKey: ["review-queue"] });
  await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
  await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  if (campaignId) {
    await queryClient.invalidateQueries({ queryKey: ["campaign-overview", String(campaignId)] });
  }
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

function reviewTone(action: DraftReviewAction) {
  if (action === "approved") {
    return "success";
  }
  if (action === "rejected" || action === "resubmitted") {
    return "warning";
  }
  return "muted";
}

function statusTone(status: ContentDraft["status"]) {
  if (status === "approved" || status === "published") {
    return "success";
  }
  if (status === "in_review" || status === "rejected") {
    return "warning";
  }
  return "muted";
}

function toDateTimeLocal(value: string | null) {
  if (!value) {
    return "";
  }

  return value.slice(0, 16);
}
