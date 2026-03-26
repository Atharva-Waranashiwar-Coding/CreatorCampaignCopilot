import type { ReactNode } from "react";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { useAuthStore } from "../../features/auth/auth-store";
import { ApiError, apiRequest } from "../../lib/api";
import { formatActionLabel, formatDateTime } from "../../lib/format";
import { queryClient } from "../../lib/query-client";
import type {
  BrandGuidelinesResponse,
  ContentDraft,
  DraftHelperArtifact,
  HelperArtifactType,
  FetchTemplatesResponse,
  HelperArtifactStatus,
  SummarizeReviewFeedbackResponse,
  ValidateContentAgainstGuidelinesResponse,
} from "../../lib/types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Input } from "../ui/input";

type CoreDraftFormInput = {
  title: string;
  platform: string;
  content_type: string;
  content_body: string;
};

type CoreHelperWorkbenchProps = {
  draft: ContentDraft;
  form: CoreDraftFormInput;
};

export function CoreHelperWorkbench({ draft, form }: CoreHelperWorkbenchProps) {
  const token = useAuthStore((state) => state.token);
  const [templateSearch, setTemplateSearch] = useState("");
  const hasBodyCopy = Boolean(form.content_body.trim());

  const artifactsQuery = useQuery({
    queryKey: ["draft-helper-artifacts", draft.id],
    queryFn: () => apiRequest<DraftHelperArtifact[]>(`/drafts/${draft.id}/helper-artifacts`, {}, token),
    enabled: Boolean(draft.id),
  });

  const invalidateArtifacts = () => {
    void queryClient.invalidateQueries({ queryKey: ["draft-helper-artifacts", draft.id] });
  };

  const saveArtifactMutation = useMutation({
    mutationFn: (payload: {
      tool_name: string;
      artifact_type: HelperArtifactType;
      title: string;
      summary: string | null;
      payload: Record<string, unknown>;
      status?: HelperArtifactStatus;
    }) =>
      apiRequest<DraftHelperArtifact>(
        `/drafts/${draft.id}/helper-artifacts`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        token,
      ),
    onSuccess: invalidateArtifacts,
  });

  const updateArtifactMutation = useMutation({
    mutationFn: ({
      artifactId,
      status,
    }: {
      artifactId: number;
      status: HelperArtifactStatus;
    }) =>
      apiRequest<DraftHelperArtifact>(
        `/drafts/${draft.id}/helper-artifacts/${artifactId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ status }),
        },
        token,
      ),
    onSuccess: invalidateArtifacts,
  });

  const deleteArtifactMutation = useMutation({
    mutationFn: (artifactId: number) =>
      apiRequest<void>(
        `/drafts/${draft.id}/helper-artifacts/${artifactId}`,
        {
          method: "DELETE",
        },
        token,
      ),
    onSuccess: invalidateArtifacts,
  });

  const guidelinesMutation = useMutation({
    mutationFn: () =>
      apiRequest<BrandGuidelinesResponse>(
        "/tools/helpers/fetch-brand-guidelines",
        {
          method: "POST",
          body: JSON.stringify({ brand_id: draft.brand_id }),
        },
        token,
      ),
  });

  const templatesMutation = useMutation({
    mutationFn: () =>
      apiRequest<FetchTemplatesResponse>(
        "/tools/helpers/fetch-templates",
        {
          method: "POST",
          body: JSON.stringify({
            brand_id: draft.brand_id,
            platform: form.platform,
            content_type: form.content_type,
            search: templateSearch || null,
            limit: 6,
          }),
        },
        token,
      ),
  });

  const validationMutation = useMutation({
    mutationFn: () =>
      apiRequest<ValidateContentAgainstGuidelinesResponse>(
        "/tools/helpers/validate-content-against-guidelines",
        {
          method: "POST",
          body: JSON.stringify({
            brand_id: draft.brand_id,
            title: form.title,
            platform: form.platform,
            content_type: form.content_type,
            content_body: form.content_body,
          }),
        },
        token,
      ),
  });

  const reviewSummaryMutation = useMutation({
    mutationFn: () =>
      apiRequest<SummarizeReviewFeedbackResponse>(
        "/tools/helpers/summarize-review-feedback",
        {
          method: "POST",
          body: JSON.stringify({ draft_id: draft.id, limit: 6 }),
        },
        token,
      ),
  });

  const artifacts = artifactsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Core helpers</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Context and review utilities</h2>
          </div>
          <Badge tone="muted">Save snapshots to draft history</Badge>
        </div>

        <p className="mt-5 rounded-[1.25rem] border border-border bg-white/80 p-4 text-sm text-muted-foreground">
          These helpers pull brand context, template context, validation signals, and review summaries directly from the current workspace.
        </p>
      </Card>

      <HelperCard
        action={(
          <Button disabled={guidelinesMutation.isPending} onClick={() => guidelinesMutation.mutate()}>
            {guidelinesMutation.isPending ? "Loading..." : "Fetch guidelines"}
          </Button>
        )}
        description="Pull the stored brand voice, audience, channels, and guidance points for the current draft."
        eyebrow="Brand context"
        title="Brand guidelines"
      >
        <MutationError error={guidelinesMutation.error} />
        {guidelinesMutation.data ? (
          <div className="mt-5 space-y-4">
            <p className="text-sm text-foreground">
              {guidelinesMutation.data.brand_name} · {guidelinesMutation.data.current_user_role}
            </p>
            <div className="flex flex-wrap gap-2">
              {guidelinesMutation.data.preferred_channels.map((channel) => (
                <Badge key={channel} tone="muted">
                  {channel}
                </Badge>
              ))}
            </div>
            <div className="grid gap-3">
              {guidelinesMutation.data.guidance_points.map((point) => (
                <div key={point} className="rounded-[1.1rem] border border-border bg-slate-50/80 p-4 text-sm text-foreground">
                  {point}
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                variant="secondary"
                onClick={() =>
                  saveArtifactMutation.mutate({
                    tool_name: "fetch_brand_guidelines",
                    artifact_type: "brand_guidelines",
                    title: "Brand guidelines snapshot",
                    summary: `${guidelinesMutation.data.brand_name} brand guidance captured for this draft.`,
                    payload: guidelinesMutation.data as unknown as Record<string, unknown>,
                  })
                }
              >
                Save snapshot
              </Button>
            </div>
          </div>
        ) : null}
      </HelperCard>

      <HelperCard
        action={(
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[220px]">
              <Input
                placeholder="Search templates"
                value={templateSearch}
                onChange={(event) => setTemplateSearch(event.target.value)}
              />
            </div>
            <Button disabled={templatesMutation.isPending} onClick={() => templatesMutation.mutate()}>
              {templatesMutation.isPending ? "Finding..." : "Fetch templates"}
            </Button>
          </div>
        )}
        description="Find reusable brand templates that already match the current platform and content type."
        eyebrow="Template context"
        title="Template retrieval"
      >
        <MutationError error={templatesMutation.error} />
        {templatesMutation.data ? (
          <div className="mt-5 space-y-3">
            <p className="text-sm text-muted-foreground">
              Returned {templatesMutation.data.returned} of {templatesMutation.data.total} matching templates.
            </p>
            {templatesMutation.data.templates.length ? (
              templatesMutation.data.templates.map((template) => (
                <div key={template.id} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge>{template.name}</Badge>
                    <Badge tone="muted">{template.template_type}</Badge>
                    {template.platform ? <Badge tone="muted">{template.platform}</Badge> : null}
                  </div>
                  <p className="mt-3 text-sm text-foreground">{template.excerpt}</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {template.content_type ?? "Flexible content type"} · Updated {formatDateTime(template.updated_at)}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No matching templates were found for the current filters.</p>
            )}
            <Button
              variant="secondary"
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "fetch_templates",
                  artifact_type: "template_snapshot",
                  title: "Template retrieval snapshot",
                  summary: `Saved ${templatesMutation.data.returned} template matches for the current draft context.`,
                  payload: templatesMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              Save snapshot
            </Button>
          </div>
        ) : null}
      </HelperCard>

      <HelperCard
        action={(
          <Button disabled={validationMutation.isPending || !hasBodyCopy} onClick={() => validationMutation.mutate()}>
            {validationMutation.isPending ? "Checking..." : "Validate content"}
          </Button>
        )}
        description="Run the deterministic guideline validator against the current draft body."
        eyebrow="Validation"
        title="Guideline validation"
      >
        <MutationError error={validationMutation.error} />
        {validationMutation.data ? (
          <div className="mt-5 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge tone={validationMutation.data.passed ? "success" : "warning"}>
                {validationMutation.data.passed ? "Pass" : "Needs revision"}
              </Badge>
              <Badge tone="muted">{validationMutation.data.score}/100</Badge>
            </div>
            <p className="text-sm text-foreground">{validationMutation.data.summary}</p>
            <div className="grid gap-3">
              {validationMutation.data.checks.map((check) => (
                <div key={check.check} className="rounded-[1.2rem] border border-border bg-slate-50/80 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge tone={check.status === "pass" ? "success" : "warning"}>{check.status}</Badge>
                    <p className="text-sm font-medium text-foreground">{formatActionLabel(check.check)}</p>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{check.detail}</p>
                </div>
              ))}
            </div>
            <Button
              variant="secondary"
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "validate_content_against_guidelines",
                  artifact_type: "validation_report",
                  title: "Guideline validation report",
                  summary: validationMutation.data.summary,
                  payload: validationMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              Save report
            </Button>
          </div>
        ) : null}
      </HelperCard>

      <HelperCard
        action={(
          <Button disabled={reviewSummaryMutation.isPending} onClick={() => reviewSummaryMutation.mutate()}>
            {reviewSummaryMutation.isPending ? "Summarizing..." : "Summarize feedback"}
          </Button>
        )}
        description="Compress the review thread into blockers, approvals, and recent decision context."
        eyebrow="Review context"
        title="Review feedback summary"
      >
        <MutationError error={reviewSummaryMutation.error} />
        {reviewSummaryMutation.data ? (
          <div className="mt-5 space-y-4">
            <p className="text-sm text-foreground">{reviewSummaryMutation.data.summary}</p>
            <div className="grid gap-4 md:grid-cols-2">
              <ResultList
                emptyMessage="No blockers identified."
                items={reviewSummaryMutation.data.blockers}
                title="Blockers"
              />
              <ResultList
                emptyMessage="No approvals noted yet."
                items={reviewSummaryMutation.data.approvals}
                title="Approvals"
              />
            </div>
            {reviewSummaryMutation.data.recent_comments.length ? (
              <div className="space-y-3">
                {reviewSummaryMutation.data.recent_comments.map((comment, index) => (
                  <div key={`${comment.created_at}-${index}`} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge>{formatActionLabel(comment.action)}</Badge>
                      <p className="text-sm text-muted-foreground">
                        {comment.actor_name ?? "Unknown user"} · {formatDateTime(comment.created_at)}
                      </p>
                    </div>
                    <p className="mt-3 text-sm text-foreground">{comment.comment}</p>
                  </div>
                ))}
              </div>
            ) : null}
            <Button
              variant="secondary"
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "summarize_review_feedback",
                  artifact_type: "review_summary",
                  title: "Review feedback summary",
                  summary: reviewSummaryMutation.data.summary,
                  payload: reviewSummaryMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              Save summary
            </Button>
          </div>
        ) : null}
      </HelperCard>

      <HelperCard
        description="Saved helper outputs stay attached to the draft so the team can revisit or mark them applied later."
        eyebrow="Saved outputs"
        title="Helper artifact history"
      >
        <MutationError error={artifactsQuery.error || saveArtifactMutation.error || updateArtifactMutation.error || deleteArtifactMutation.error} />
        {artifactsQuery.isLoading ? (
          <p className="mt-5 text-sm text-muted-foreground">Loading saved helper artifacts...</p>
        ) : artifacts.length ? (
          <div className="mt-5 space-y-3">
            {artifacts.map((artifact) => (
              <div key={artifact.id} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge>{formatActionLabel(artifact.tool_name)}</Badge>
                  <Badge tone={artifactStatusTone(artifact.status)}>{artifact.status}</Badge>
                </div>
                <p className="mt-3 text-sm font-medium text-foreground">{artifact.title}</p>
                {artifact.summary ? (
                  <p className="mt-2 text-sm text-muted-foreground">{artifact.summary}</p>
                ) : null}
                <p className="mt-2 text-sm text-muted-foreground">
                  {artifact.creator_name ?? "Unknown user"} · {formatDateTime(artifact.updated_at)}
                </p>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words rounded-[1rem] bg-slate-50/90 p-3 text-xs leading-5 text-slate-700">
                  {truncateJson(artifact.payload)}
                </pre>
                <div className="mt-4 flex flex-wrap gap-2">
                  {artifact.status !== "applied" ? (
                    <Button
                      variant="secondary"
                      onClick={() => updateArtifactMutation.mutate({ artifactId: artifact.id, status: "applied" })}
                    >
                      Mark applied
                    </Button>
                  ) : null}
                  {artifact.status !== "dismissed" ? (
                    <Button
                      variant="ghost"
                      onClick={() => updateArtifactMutation.mutate({ artifactId: artifact.id, status: "dismissed" })}
                    >
                      Dismiss
                    </Button>
                  ) : null}
                  <Button
                    variant="ghost"
                    onClick={() => {
                      if (window.confirm(`Delete ${artifact.title}?`)) {
                        deleteArtifactMutation.mutate(artifact.id);
                      }
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-5 text-sm text-muted-foreground">
            Saved guideline reports, summaries, and template snapshots will appear here once you preserve them.
          </p>
        )}
      </HelperCard>
    </div>
  );
}

function HelperCard({
  eyebrow,
  title,
  description,
  action,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-3 text-sm text-muted-foreground">{description}</p>
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}

function MutationError({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error.message}
    </p>
  );
}

function ResultList({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: string[];
  emptyMessage: string;
}) {
  return (
    <div className="rounded-[1.2rem] border border-border bg-slate-50/80 p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length ? (
          items.map((item) => (
            <p key={item} className="text-sm text-foreground">
              {item}
            </p>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        )}
      </div>
    </div>
  );
}

function artifactStatusTone(status: HelperArtifactStatus) {
  if (status === "applied") {
    return "success";
  }
  if (status === "dismissed") {
    return "warning";
  }
  return "muted";
}

function truncateJson(value: Record<string, unknown>) {
  const text = JSON.stringify(value ?? {}, null, 2);
  if (text.length <= 480) {
    return text;
  }
  return `${text.slice(0, 477).trimEnd()}...`;
}
