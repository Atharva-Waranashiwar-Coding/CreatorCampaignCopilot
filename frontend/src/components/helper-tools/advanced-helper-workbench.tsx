import type { ReactNode } from "react";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { useAuthStore } from "../../features/auth/auth-store";
import { ApiError, apiRequest } from "../../lib/api";
import { formatActionLabel, formatDateTime } from "../../lib/format";
import { queryClient } from "../../lib/query-client";
import type {
  AdvancedToolExecution,
  AssetRecommendationResponse,
  BrandVoiceValidatorResponse,
  ContentDraft,
  CrossChannelAdaptationResponse,
  DraftHelperArtifact,
  HelperArtifactStatus,
  HelperArtifactType,
  ReviewFeedbackToRevisionChecklistResponse,
  ToolUsageLog,
  TemplateRecommendationResponse,
  ValidationCheckStatus,
} from "../../lib/types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Label } from "../ui/label";
import { Select } from "../ui/select";

type AdvancedDraftFormInput = {
  title: string;
  platform: string;
  content_type: string;
  content_body: string;
};

type AdvancedHelperWorkbenchProps = {
  draft: ContentDraft;
  form: AdvancedDraftFormInput;
  onReplaceDraftValues: (next: { title?: string | null; contentBody: string }) => void;
  onInsertBodySnippet: (snippet: string) => void;
};

const TARGET_PLATFORM_OPTIONS = ["LinkedIn", "Instagram", "Email", "Article"];

export function AdvancedHelperWorkbench({
  draft,
  form,
  onReplaceDraftValues,
  onInsertBodySnippet,
}: AdvancedHelperWorkbenchProps) {
  const token = useAuthStore((state) => state.token);
  const [targetPlatform, setTargetPlatform] = useState(getDefaultTargetPlatform(form.platform));
  const hasBodyCopy = Boolean(form.content_body.trim());

  const recentUsageQuery = useQuery({
    queryKey: ["helper-tools", "usage", "advanced", draft.id],
    queryFn: () =>
      apiRequest<ToolUsageLog[]>(
        `/tools/usage?limit=8&advanced_only=true&draft_id=${draft.id}`,
        {},
        token,
      ),
    enabled: Boolean(draft.id),
  });

  const invalidateAdvancedUsage = () => {
    void queryClient.invalidateQueries({ queryKey: ["helper-tools", "usage"] });
    void queryClient.invalidateQueries({ queryKey: ["helper-tools", "usage", "advanced", draft.id] });
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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["draft-helper-artifacts", draft.id] });
    },
  });

  const voiceMutation = useMutation({
    mutationFn: () =>
      apiRequest<BrandVoiceValidatorResponse>(
        "/tools/helpers/brand-voice-validator",
        {
          method: "POST",
          body: JSON.stringify(buildDraftContextPayload(draft, form)),
        },
        token,
      ),
    onSuccess: invalidateAdvancedUsage,
  });

  const adaptationMutation = useMutation({
    mutationFn: () =>
      apiRequest<CrossChannelAdaptationResponse>(
        "/tools/helpers/cross-channel-adaptation",
        {
          method: "POST",
          body: JSON.stringify({
            ...buildDraftContextPayload(draft, form),
            source_platform: form.platform,
            target_platform: targetPlatform,
          }),
        },
        token,
      ),
    onSuccess: invalidateAdvancedUsage,
  });

  const templateMutation = useMutation({
    mutationFn: () =>
      apiRequest<TemplateRecommendationResponse>(
        "/tools/helpers/template-recommendation",
        {
          method: "POST",
          body: JSON.stringify(buildDraftContextPayload(draft, form)),
        },
        token,
      ),
    onSuccess: invalidateAdvancedUsage,
  });

  const assetMutation = useMutation({
    mutationFn: () =>
      apiRequest<AssetRecommendationResponse>(
        "/tools/helpers/asset-recommendation",
        {
          method: "POST",
          body: JSON.stringify(buildDraftContextPayload(draft, form)),
        },
        token,
      ),
    onSuccess: invalidateAdvancedUsage,
  });

  const checklistMutation = useMutation({
    mutationFn: () =>
      apiRequest<ReviewFeedbackToRevisionChecklistResponse>(
        "/tools/helpers/review-feedback-to-revision-checklist",
        {
          method: "POST",
          body: JSON.stringify({ draft_id: draft.id, limit: 10 }),
        },
        token,
      ),
    onSuccess: invalidateAdvancedUsage,
  });

  const recentUsage = recentUsageQuery.data ?? [];
  const adaptationResult = adaptationMutation.data;

  return (
    <div className="space-y-6">
      <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Advanced helpers</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Optional content operations</h2>
          </div>
          <Badge tone="muted">Does not auto-save</Badge>
        </div>

        <p className="mt-5 rounded-[1.25rem] border border-border bg-white/80 p-4 text-sm text-muted-foreground">
          Run validation, adaptation, recommendation, and feedback-conversion helpers directly against the current draft.
          The saved draft only changes if you apply a result here and then use the standard save action above.
        </p>
        <MutationError error={saveArtifactMutation.error} />
      </Card>

      <ToolCard
        action={
          <Button disabled={voiceMutation.isPending || !hasBodyCopy} onClick={() => voiceMutation.mutate()}>
            {voiceMutation.isPending ? "Validating..." : "Run validator"}
          </Button>
        }
        description="Check the current draft body against the stored brand voice, audience cues, and preferred channels."
        eyebrow="Brand voice"
        title="Voice validation"
      >
        <MutationError error={voiceMutation.error} />

        {voiceMutation.data ? (
          <div className="mt-5 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge tone={voiceTone(voiceMutation.data.verdict)}>{voiceMutation.data.verdict}</Badge>
              <Badge tone="muted">{voiceMutation.data.score}/100</Badge>
            </div>
            <ExecutionMeta execution={voiceMutation.data.execution} />
            <p className="text-sm text-foreground">{voiceMutation.data.summary}</p>
            <div className="grid gap-3">
              {voiceMutation.data.checks.map((check) => (
                <div key={check.check} className="rounded-[1.2rem] border border-border bg-slate-50/80 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge tone={validationTone(check.status)}>{check.status}</Badge>
                    <p className="text-sm font-medium text-foreground">{formatActionLabel(check.check)}</p>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{check.detail}</p>
                </div>
              ))}
            </div>
            {voiceMutation.data.revision_suggestions.length ? (
              <div className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Suggested revisions</p>
                <div className="mt-3 space-y-2">
                  {voiceMutation.data.revision_suggestions.map((suggestion) => (
                    <p key={suggestion} className="text-sm text-foreground">
                      {suggestion}
                    </p>
                  ))}
                </div>
              </div>
            ) : null}
            <Button
              variant="secondary"
              disabled={saveArtifactMutation.isPending}
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "brand_voice_validator",
                  artifact_type: "voice_validation",
                  title: "Brand voice validation",
                  summary: voiceMutation.data.summary,
                  payload: voiceMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              {saveArtifactMutation.isPending ? "Saving..." : "Save validation"}
            </Button>
          </div>
        ) : null}
      </ToolCard>

      <ToolCard
        action={
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[200px]">
              <Label>Target platform</Label>
              <Select value={targetPlatform} onChange={(event) => setTargetPlatform(event.target.value)}>
                {TARGET_PLATFORM_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            </div>
            <Button disabled={adaptationMutation.isPending || !hasBodyCopy} onClick={() => adaptationMutation.mutate()}>
              {adaptationMutation.isPending ? "Adapting..." : "Adapt draft"}
            </Button>
          </div>
        }
        description="Generate a platform-shaped draft variant without changing the saved draft until you apply it."
        eyebrow="Channel adaptation"
        title="Cross-channel draft adaptation"
      >
        <MutationError error={adaptationMutation.error} />

        {adaptationResult ? (
          <div className="mt-5 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge>{adaptationResult.source_platform}</Badge>
              <Badge tone="muted">to</Badge>
              <Badge>{adaptationResult.target_platform}</Badge>
            </div>
            <ExecutionMeta execution={adaptationResult.execution} />
            <div className="rounded-[1.2rem] border border-border bg-slate-50/80 p-4">
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Suggested adaptation</p>
              {adaptationResult.adapted_title ? (
                <p className="mt-3 text-base font-semibold text-foreground">{adaptationResult.adapted_title}</p>
              ) : null}
              <pre className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground">{adaptationResult.adapted_body}</pre>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                onClick={() =>
                  onReplaceDraftValues({
                    title: adaptationResult.adapted_title ?? form.title,
                    contentBody: adaptationResult.adapted_body,
                  })
                }
              >
                Use title and body
              </Button>
              <Button variant="secondary" onClick={() => onInsertBodySnippet(adaptationResult.adapted_body)}>
                Insert body below draft
              </Button>
              <Button
                variant="secondary"
                disabled={saveArtifactMutation.isPending}
                onClick={() =>
                  saveArtifactMutation.mutate({
                    tool_name: "cross_channel_adaptation",
                    artifact_type: "cross_channel_adaptation",
                    title: `Cross-channel adaptation for ${adaptationResult.target_platform}`,
                    summary: `Adapted ${adaptationResult.source_platform} draft for ${adaptationResult.target_platform}.`,
                    payload: adaptationResult as unknown as Record<string, unknown>,
                  })
                }
              >
                {saveArtifactMutation.isPending ? "Saving..." : "Save adaptation"}
              </Button>
            </div>
            {adaptationResult.adaptation_notes.length ? (
              <div className="grid gap-2">
                {adaptationResult.adaptation_notes.map((note) => (
                  <p key={note} className="text-sm text-muted-foreground">
                    {note}
                  </p>
                ))}
              </div>
            ) : null}
            {adaptationResult.derived_hashtags.length ? (
              <div className="flex flex-wrap gap-2">
                {adaptationResult.derived_hashtags.map((tag) => (
                  <Badge key={tag} tone="muted">
                    {tag}
                  </Badge>
                ))}
              </div>
            ) : null}
            {adaptationResult.warnings.length ? (
              <div className="space-y-2 rounded-[1.2rem] border border-amber-200 bg-amber-50 p-4">
                {adaptationResult.warnings.map((warning) => (
                  <p key={warning} className="text-sm text-amber-900">
                    {warning}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </ToolCard>

      <ToolCard
        action={
          <Button disabled={templateMutation.isPending} onClick={() => templateMutation.mutate()}>
            {templateMutation.isPending ? "Ranking..." : "Recommend templates"}
          </Button>
        }
        description="Find the brand templates that best match the current draft topic, platform, and content shape."
        eyebrow="Template fit"
        title="Template recommendation"
      >
        <MutationError error={templateMutation.error} />

        {templateMutation.data ? (
          <div className="mt-5 space-y-3">
            <ExecutionMeta execution={templateMutation.data.execution} />
            {templateMutation.data.recommendations.length ? (
              templateMutation.data.recommendations.map((item) => (
                <div key={item.id} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge>{item.name}</Badge>
                    <Badge tone="muted">{item.score}/100</Badge>
                    <Badge tone="muted">{item.template_type}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-foreground">{item.excerpt}</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {item.platform ?? "Flexible platform"}{item.content_type ? ` · ${item.content_type}` : ""} · Updated{" "}
                    {formatDateTime(item.updated_at)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {item.reasons.map((reason) => (
                      <Badge key={reason} tone="muted">
                        {reason}
                      </Badge>
                    ))}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No templates are available for this brand yet.</p>
            )}
            <Button
              variant="secondary"
              disabled={saveArtifactMutation.isPending}
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "template_recommendation",
                  artifact_type: "template_recommendations",
                  title: "Template recommendations",
                  summary: `Saved ${templateMutation.data.recommendations.length} ranked template recommendations.`,
                  payload: templateMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              {saveArtifactMutation.isPending ? "Saving..." : "Save recommendations"}
            </Button>
          </div>
        ) : null}
      </ToolCard>

      <ToolCard
        action={
          <Button disabled={assetMutation.isPending} onClick={() => assetMutation.mutate()}>
            {assetMutation.isPending ? "Matching..." : "Recommend assets"}
          </Button>
        }
        description="Rank campaign assets against the current draft so supporting visuals and files are easier to pull in."
        eyebrow="Asset fit"
        title="Asset recommendation"
      >
        <MutationError error={assetMutation.error} />

        {assetMutation.data ? (
          <div className="mt-5 space-y-3">
            <ExecutionMeta execution={assetMutation.data.execution} />
            {assetMutation.data.recommendations.length ? (
              assetMutation.data.recommendations.map((asset) => (
                <div key={asset.id} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge>{asset.name}</Badge>
                    <Badge tone="muted">{asset.score}/100</Badge>
                    <Badge tone="muted">{asset.asset_type}</Badge>
                  </div>
                  <p className="mt-3 text-sm text-muted-foreground">
                    {asset.notes ?? "No asset notes provided."}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {asset.reasons.map((reason) => (
                      <Badge key={reason} tone="muted">
                        {reason}
                      </Badge>
                    ))}
                  </div>
                  <a
                    className="mt-4 inline-flex text-sm font-medium text-primary"
                    href={asset.file_url}
                    rel="noreferrer"
                    target="_blank"
                  >
                    Open asset
                  </a>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No campaign assets are available to rank yet.</p>
            )}
            <Button
              variant="secondary"
              disabled={saveArtifactMutation.isPending}
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "asset_recommendation",
                  artifact_type: "asset_recommendations",
                  title: "Asset recommendations",
                  summary: `Saved ${assetMutation.data.recommendations.length} ranked asset recommendations.`,
                  payload: assetMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              {saveArtifactMutation.isPending ? "Saving..." : "Save recommendations"}
            </Button>
          </div>
        ) : null}
      </ToolCard>

      <ToolCard
        action={
          <Button disabled={checklistMutation.isPending} onClick={() => checklistMutation.mutate()}>
            {checklistMutation.isPending ? "Converting..." : "Build checklist"}
          </Button>
        }
        description="Turn review comments into a clear revision checklist before the next edit and resubmission cycle."
        eyebrow="Feedback conversion"
        title="Revision checklist"
      >
        <MutationError error={checklistMutation.error} />

        {checklistMutation.data ? (
          <div className="mt-5 space-y-4">
            <ExecutionMeta execution={checklistMutation.data.execution} />
            <p className="text-sm text-foreground">{checklistMutation.data.summary}</p>
            <div className="space-y-3">
              {checklistMutation.data.checklist_items.map((item) => (
                <div key={`${item.item}-${item.source_excerpt}`} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge tone={priorityTone(item.priority)}>{item.priority}</Badge>
                    <Badge tone="muted">{formatActionLabel(item.source_action)}</Badge>
                  </div>
                  <p className="mt-3 text-sm font-medium text-foreground">{item.item}</p>
                  <p className="mt-2 text-sm text-muted-foreground">{item.guidance}</p>
                  <p className="mt-2 text-sm text-muted-foreground">Source: {item.source_excerpt}</p>
                </div>
              ))}
            </div>
            {checklistMutation.data.preserved_strengths.length ? (
              <div className="rounded-[1.2rem] border border-border bg-slate-50/80 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Keep from approved feedback</p>
                <div className="mt-3 space-y-2">
                  {checklistMutation.data.preserved_strengths.map((strength) => (
                    <p key={strength} className="text-sm text-foreground">
                      {strength}
                    </p>
                  ))}
                </div>
              </div>
            ) : null}
            <Button
              variant="secondary"
              disabled={saveArtifactMutation.isPending}
              onClick={() =>
                saveArtifactMutation.mutate({
                  tool_name: "review_feedback_to_revision_checklist",
                  artifact_type: "revision_checklist",
                  title: "Revision checklist",
                  summary: checklistMutation.data.summary,
                  payload: checklistMutation.data as unknown as Record<string, unknown>,
                })
              }
            >
              {saveArtifactMutation.isPending ? "Saving..." : "Save checklist"}
            </Button>
          </div>
        ) : null}
      </ToolCard>

      <ToolCard
        description="Inspect recent advanced helper executions for this draft, including compact request/result traces."
        eyebrow="Recent activity"
        title="Advanced helper usage"
      >
        {recentUsageQuery.isLoading ? (
          <p className="mt-5 text-sm text-muted-foreground">Loading recent advanced helper runs...</p>
        ) : recentUsage.length ? (
          <div className="mt-5 space-y-3">
            {recentUsage.map((item) => (
              <div key={item.id} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge>{formatActionLabel(item.tool_name)}</Badge>
                  <Badge tone={item.was_successful ? "success" : "warning"}>
                    {item.was_successful ? "Success" : "Failed"}
                  </Badge>
                  <Badge tone="muted">{item.invocation_source}</Badge>
                </div>
                <p className="mt-3 text-sm text-foreground">
                  {item.actor_name ?? "Unknown user"} · {formatDateTime(item.created_at)}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">{extractUsageSummary(item)}</p>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words rounded-[1rem] bg-slate-50/90 p-3 text-xs leading-5 text-slate-700">
                  {truncateJson(item.result_trace ?? item.result_summary)}
                </pre>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-5 text-sm text-muted-foreground">
            Advanced helper runs will appear here after you validate tone, adapt copy, or request recommendations.
          </p>
        )}
      </ToolCard>
    </div>
  );
}

function buildDraftContextPayload(draft: ContentDraft, form: AdvancedDraftFormInput) {
  return {
    draft_id: draft.id,
    brand_id: draft.brand_id,
    campaign_id: draft.campaign_id,
    title: form.title,
    platform: form.platform,
    content_type: form.content_type,
    content_body: form.content_body,
  };
}

function ToolCard({
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

function ExecutionMeta({ execution }: { execution: AdvancedToolExecution }) {
  const tone =
    execution.mode === "llm" ? "success" : execution.mode === "deterministic_fallback" ? "warning" : "muted";
  const label =
    execution.mode === "llm"
      ? "LLM-backed"
      : execution.mode === "deterministic_fallback"
        ? "LLM fallback"
        : "Deterministic";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={tone}>{label}</Badge>
        {execution.provider_name ? <Badge tone="muted">{execution.provider_name}</Badge> : null}
        {execution.model ? <Badge tone="muted">{execution.model}</Badge> : null}
      </div>
      {execution.fallback_reason ? (
        <p className="rounded-[1rem] border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {execution.fallback_reason}
        </p>
      ) : null}
    </div>
  );
}

function validationTone(status: ValidationCheckStatus) {
  if (status === "pass") {
    return "success";
  }
  if (status === "warn") {
    return "warning";
  }
  return "warning";
}

function voiceTone(verdict: BrandVoiceValidatorResponse["verdict"]) {
  if (verdict === "pass") {
    return "success";
  }
  if (verdict === "warn") {
    return "warning";
  }
  return "warning";
}

function priorityTone(priority: ReviewFeedbackToRevisionChecklistResponse["checklist_items"][number]["priority"]) {
  if (priority === "high") {
    return "warning";
  }
  if (priority === "medium") {
    return "muted";
  }
  return "success";
}

function getDefaultTargetPlatform(currentPlatform: string) {
  const current = currentPlatform.toLowerCase();
  const fallback = TARGET_PLATFORM_OPTIONS.find((option) => option.toLowerCase() !== current);
  return fallback ?? TARGET_PLATFORM_OPTIONS[0];
}

function extractUsageSummary(item: ToolUsageLog) {
  const traceSummary = item.result_trace?.summary;
  if (typeof traceSummary === "string" && traceSummary.trim()) {
    return traceSummary;
  }

  if (!item.was_successful && item.error_detail) {
    return item.error_detail;
  }

  return `Target ${formatActionLabel(item.target_entity_type)} ${item.target_entity_id ? `#${item.target_entity_id}` : "context"}.`;
}

function truncateJson(value: Record<string, unknown> | null | undefined) {
  const text = JSON.stringify(value ?? {}, null, 2);
  if (text.length <= 420) {
    return text;
  }
  return `${text.slice(0, 417).trimEnd()}...`;
}
