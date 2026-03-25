import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { CampaignPlanner } from "../components/campaign-planning/campaign-planner";
import { AssignmentPanel } from "../components/collaboration/assignment-panel";
import { ThreadedCommentsCard } from "../components/collaboration/threaded-comments-card";
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
import { formatActionLabel, formatDate, formatDateTime, formatStatusLabel } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type {
  Assignment,
  AuditLog,
  CampaignAsset,
  CampaignDependency,
  CampaignMilestone,
  CampaignOverview,
  CollaborationComment,
  ContentDraft,
  DraftStatus,
  Membership,
} from "../lib/types";

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

type AssetFormState = {
  name: string;
  asset_type: string;
  file_url: string;
  thumbnail_url: string;
  mime_type: string;
  file_size_bytes: string;
  notes: string;
};

type MilestoneFormState = {
  target_date: string;
  notes: string;
};

type DependencyFormState = {
  dependent_node: string;
  blocker_node: string;
  note: string;
};

type DependencyNodeOption = {
  value: string;
  label: string;
};

const emptyBriefForm: BriefFormState = {
  key_message: "",
  call_to_action: "",
  tone: "",
  channels: "",
  themes: "",
  references: "",
};

const emptyAssetForm: AssetFormState = {
  name: "",
  asset_type: "",
  file_url: "",
  thumbnail_url: "",
  mime_type: "",
  file_size_bytes: "",
  notes: "",
};

const emptyDependencyForm: DependencyFormState = {
  dependent_node: "",
  blocker_node: "",
  note: "",
};

export function CampaignOverviewPage() {
  const { campaignId } = useParams();
  const token = useAuthStore((state) => state.token);
  const currentUser = useAuthStore((state) => state.user);
  const [briefForm, setBriefForm] = useState<BriefFormState>(emptyBriefForm);
  const [draftForm, setDraftForm] = useState<DraftFormState>(buildEmptyDraftForm("draft"));
  const [assetForm, setAssetForm] = useState<AssetFormState>(emptyAssetForm);
  const [editingAssetId, setEditingAssetId] = useState<number | null>(null);
  const [milestoneForms, setMilestoneForms] = useState<Record<number, MilestoneFormState>>({});
  const [dependencyForm, setDependencyForm] = useState<DependencyFormState>(emptyDependencyForm);

  const overviewQuery = useQuery({
    queryKey: ["campaign-overview", campaignId],
    queryFn: () => apiRequest<CampaignOverview>(`/campaigns/${campaignId}/overview`, {}, token),
    enabled: Boolean(campaignId),
  });

  const commentsQuery = useQuery({
    queryKey: ["campaign-comments", campaignId],
    queryFn: () => apiRequest<CollaborationComment[]>(`/campaigns/${campaignId}/comments`, {}, token),
    enabled: Boolean(campaignId),
  });

  const assignmentsQuery = useQuery({
    queryKey: ["campaign-assignments", campaignId],
    queryFn: () => apiRequest<Assignment[]>(`/campaigns/${campaignId}/assignments`, {}, token),
    enabled: Boolean(campaignId),
  });

  const membershipsQuery = useQuery({
    queryKey: ["brand-memberships", overviewQuery.data?.campaign.brand_id],
    queryFn: () => apiRequest<Membership[]>(`/brands/${overviewQuery.data?.campaign.brand_id}/memberships`, {}, token),
    enabled: Boolean(overviewQuery.data?.campaign.brand_id),
  });

  const overview = overviewQuery.data;
  const campaign = overview?.campaign;
  const currentMembership = membershipsQuery.data?.find((membership) => membership.user_id === currentUser?.id) ?? null;
  const workflow = overview?.draft_workflow;
  const defaultDraftStatus = workflow?.initial_stage_keys[0] ?? workflow?.stages[0]?.key ?? "draft";
  const draftCreateStages =
    workflow?.stages.filter((stage) => workflow.initial_stage_keys.includes(stage.key)).length
      ? workflow.stages.filter((stage) => workflow.initial_stage_keys.includes(stage.key))
      : workflow?.stages ?? [];
  const canManageWorkflow = currentMembership ? ["owner", "admin", "editor"].includes(currentMembership.role) : false;
  const unresolvedDependencies = overview?.dependencies.filter((dependency) => !dependency.is_satisfied) ?? [];
  const blockedDraftReasons = buildDraftBlockerMap(unresolvedDependencies);
  const blockedMilestoneReasons = buildMilestoneBlockerMap(unresolvedDependencies);
  const dependencyNodeOptions = overview
    ? buildDependencyNodeOptions({
        drafts: overview.drafts,
        milestones: overview.milestones,
        workflow: overview.draft_workflow,
      })
    : [];

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

  useEffect(() => {
    setDraftForm((current) => {
      if (workflow?.stages.some((stage) => stage.key === current.status)) {
        return current;
      }

      return {
        ...current,
        status: defaultDraftStatus,
      };
    });
  }, [defaultDraftStatus, workflow]);

  useEffect(() => {
    if (!overview?.milestones.length) {
      setMilestoneForms({});
      return;
    }

    setMilestoneForms(
      Object.fromEntries(
        overview.milestones.map((milestone) => [
          milestone.id,
          {
            target_date: milestone.target_date ?? "",
            notes: milestone.notes ?? "",
          },
        ]),
      ),
    );
  }, [overview?.milestones]);

  const createOrUpdateBriefMutation = useMutation({
    mutationFn: () =>
      apiRequest(
        `/campaigns/${campaignId}/brief`,
        {
          method: "PUT",
          body: JSON.stringify({
            ...briefForm,
            channels: splitList(briefForm.channels),
            themes: splitList(briefForm.themes),
          }),
        },
        token,
      ),
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
      apiRequest(
        `/drafts`,
        {
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
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      setDraftForm(buildEmptyDraftForm(defaultDraftStatus));
    },
  });

  const saveAssetMutation = useMutation({
    mutationFn: () =>
      apiRequest(
        `/campaigns/${campaignId}/assets${editingAssetId ? `/${editingAssetId}` : ""}`,
        {
          method: editingAssetId ? "PATCH" : "POST",
          body: JSON.stringify({
            name: assetForm.name,
            asset_type: assetForm.asset_type,
            file_url: assetForm.file_url,
            thumbnail_url: assetForm.thumbnail_url || null,
            mime_type: assetForm.mime_type || null,
            file_size_bytes: assetForm.file_size_bytes ? Number(assetForm.file_size_bytes) : null,
            notes: assetForm.notes || null,
          }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      setEditingAssetId(null);
      setAssetForm(emptyAssetForm);
    },
  });

  const deleteAssetMutation = useMutation({
    mutationFn: (assetId: number) =>
      apiRequest<void>(`/campaigns/${campaignId}/assets/${assetId}`, {
        method: "DELETE",
      }, token),
    onSuccess: (_, assetId) => {
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      if (editingAssetId === assetId) {
        setEditingAssetId(null);
        setAssetForm(emptyAssetForm);
      }
    },
  });

  const commentMutation = useMutation({
    mutationFn: (payload: { body: string; parent_comment_id: number | null }) =>
      apiRequest<CollaborationComment[]>(
        `/campaigns/${campaignId}/comments`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        token,
      ),
    onSuccess: (comments) => {
      queryClient.setQueryData(["campaign-comments", campaignId], comments);
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const createAssignmentMutation = useMutation({
    mutationFn: (payload: {
      assignee_user_id: number;
      note: string | null;
      due_at: string | null;
    }) =>
      apiRequest<Assignment[]>(
        `/campaigns/${campaignId}/assignments`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        token,
      ),
    onSuccess: (assignments) => {
      queryClient.setQueryData(["campaign-assignments", campaignId], assignments);
      queryClient.invalidateQueries({ queryKey: ["assignments", "mine"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const completeAssignmentMutation = useMutation({
    mutationFn: (assignmentId: number) =>
      apiRequest<Assignment>(
        `/assignments/${assignmentId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ status: "completed" }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign-assignments", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["assignments", "mine"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const moveDraftStageMutation = useMutation({
    mutationFn: ({ draft, targetStatus }: { draft: ContentDraft; targetStatus: DraftStatus }) =>
      apiRequest<ContentDraft>(
        `/drafts/${draft.id}/move-stage`,
        {
          method: "POST",
          body: JSON.stringify({ target_status: targetStatus }),
        },
        token,
      ),
    onSuccess: async (draft) => {
      await queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      await queryClient.invalidateQueries({ queryKey: ["drafts"] });
      await queryClient.invalidateQueries({ queryKey: ["draft", String(draft.id)] });
      await queryClient.invalidateQueries({ queryKey: ["draft-reviews", String(draft.id)] });
      await queryClient.invalidateQueries({ queryKey: ["draft-versions", String(draft.id)] });
      await queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const updateMilestoneMutation = useMutation({
    mutationFn: ({ milestoneId, payload }: { milestoneId: number; payload: Record<string, boolean | string | null> }) =>
      apiRequest<CampaignMilestone>(
        `/campaigns/${campaignId}/milestones/${milestoneId}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
        token,
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      await queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
    },
  });

  const createDependencyMutation = useMutation({
    mutationFn: (payload: Record<string, number | string | null>) =>
      apiRequest<CampaignDependency[]>(
        `/campaigns/${campaignId}/dependencies`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        token,
      ),
    onSuccess: async () => {
      setDependencyForm(emptyDependencyForm);
      await queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

  const deleteDependencyMutation = useMutation({
    mutationFn: (dependencyId: number) =>
      apiRequest<CampaignDependency[]>(
        `/campaigns/${campaignId}/dependencies/${dependencyId}`,
        {
          method: "DELETE",
        },
        token,
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["campaign-overview", campaignId] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["drafts"] });
    },
  });

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
            <Link
              className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              to="/campaigns"
            >
              Back to campaigns
            </Link>
          </div>
        }
      />

      <Card className="border-white/70 bg-white/90 p-6 shadow-xl shadow-slate-900/5">
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Workspace snapshot</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight">Keep the brief, pipeline, and schedule moving together</h2>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-muted-foreground">
              {campaign.objective
                ? campaign.objective
                : "This campaign still needs a sharper objective. Use the brief below to define the narrative, CTA, and channel plan before content production accelerates."}
            </p>

            <div className="mt-5 flex flex-wrap gap-2">
              <Badge tone={campaign.status === "active" ? "success" : "muted"}>{campaign.status}</Badge>
              <Badge tone="muted">{overview.planning_summary.total_drafts} drafts</Badge>
              <Badge tone="muted">{overview.assets.length} assets</Badge>
              {overview.brief?.channels.slice(0, 3).map((channel) => (
                <Badge key={channel}>{channel}</Badge>
              ))}
            </div>

            <div className="mt-6 grid gap-3 md:grid-cols-3">
              <WorkspaceSummaryCard
                hint="Ideas, active drafts, and revisions still in progress."
                label="Backlog"
                value={overview.planning_summary.idea_count + overview.planning_summary.draft_count + overview.planning_summary.rejected_count}
              />
              <WorkspaceSummaryCard
                hint="Pieces sitting with reviewers right now."
                label="Awaiting Review"
                value={overview.planning_summary.in_review_count}
              />
              <WorkspaceSummaryCard
                hint="Earliest scheduled publish date across the campaign."
                label="Next Publish"
                value={overview.planning_summary.next_planned_publish_at ? formatDateTime(overview.planning_summary.next_planned_publish_at) : "Not set"}
              />
            </div>
          </div>

          <div className="rounded-[1.5rem] border border-border bg-white/85 p-5">
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Quick actions</p>
            <h3 className="mt-2 text-xl font-semibold tracking-tight">Jump to the next planning move</h3>
            <div className="mt-5 grid gap-2">
              <QuickAction href="#campaign-brief" label="Refine the campaign brief" />
              <QuickAction href="#campaign-composer" label="Create or update a working draft" />
              <QuickAction href="#campaign-milestones" label="Track milestones" />
              <QuickAction href="#campaign-dependencies" label="Review blockers and dependencies" />
              <QuickAction href="#campaign-planner" label="Organize drafts in the planner" />
              <QuickAction href="#campaign-assets" label="Review the asset library" />
            </div>

            <div className="mt-5 rounded-[1.25rem] bg-muted/60 px-4 py-4">
              <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Coverage</p>
              <p className="mt-2 text-sm leading-6 text-foreground">
                {overview.brief?.channels.length
                  ? `Planned channels: ${overview.brief.channels.join(", ")}.`
                  : "No channels are defined in the brief yet."}
              </p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                {campaign.audience ? `Audience: ${campaign.audience}` : "Audience definition is still blank."}
              </p>
            </div>
          </div>
        </div>
      </Card>

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Drafts" value={overview.drafts.length} />
        <MetricCard label="Assets" value={overview.assets.length} />
        <MetricCard label="Scheduled" value={overview.schedule.length} />
        <MetricCard label="Brief" value={overview.brief ? "Ready" : "Missing"} />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="scroll-mt-24 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="campaign-brief">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Content brief</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign brief</h2>
            </div>
            {overview.brief ? <Badge tone="success">Saved</Badge> : <Badge tone="warning">Draft</Badge>}
          </div>

          {campaign.objective || campaign.audience ? (
            <div className="mt-4 rounded-[1.25rem] border border-border bg-white/80 p-4">
              <p className="text-sm text-muted-foreground">{campaign.objective ?? "Objective not set yet."}</p>
              <p className="mt-2 text-sm text-muted-foreground">{campaign.audience ?? "Audience not set yet."}</p>
            </div>
          ) : (
            <div className="mt-4 rounded-[1.25rem] border border-dashed border-border bg-white/80 p-4">
              <p className="text-sm font-medium text-foreground">Start by setting the core brief signal</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Add an objective, audience, and channel plan so creators know what this campaign needs to achieve before the copy starts branching into channel-specific drafts.
              </p>
            </div>
          )}

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
          <Card className="scroll-mt-24 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="campaign-composer">
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
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={statusTone(item.status_type)}>{item.status_label}</Badge>
                  </div>
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
                <Field label="Starting stage">
                  <Select
                    value={draftForm.status}
                    onChange={(event) => setDraftForm((current) => ({ ...current, status: event.target.value as DraftStatus }))}
                  >
                    {draftCreateStages.map((stage) => (
                      <option key={stage.key} value={stage.key}>
                        {stage.label}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              <Field label="Planned publish at">
                <Input
                  type="datetime-local"
                  value={draftForm.planned_publish_at}
                  onChange={(event) => setDraftForm((current) => ({ ...current, planned_publish_at: event.target.value }))}
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

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <Card className="scroll-mt-24 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="campaign-milestones">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Milestone tracker</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign milestones</h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="muted">
                {overview.milestones.filter((milestone) => milestone.is_complete).length}/{overview.milestones.length} complete
              </Badge>
              {blockedMilestoneCount(blockedMilestoneReasons) ? (
                <Badge tone="warning">{blockedMilestoneCount(blockedMilestoneReasons)} blocked</Badge>
              ) : null}
            </div>
          </div>

          <p className="mt-4 text-sm leading-6 text-muted-foreground">
            Default campaign checkpoints stay visible here even as each brand uses its own draft workflow. Dependencies can block milestone completion until prerequisite work is done.
          </p>

          {!canManageWorkflow ? (
            <div className="mt-4 rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 text-sm text-muted-foreground">
              Reviewers and viewers can track milestone progress here, but only workspace managers can edit target dates, notes, and completion.
            </div>
          ) : null}

          <MutationFeedback error={updateMilestoneMutation.error} />

          <div className="mt-5 space-y-4">
            {overview.milestones.map((milestone) => {
              const form = milestoneForms[milestone.id] ?? {
                target_date: milestone.target_date ?? "",
                notes: milestone.notes ?? "",
              };
              const blockers = blockedMilestoneReasons[milestone.id] ?? [];
              const isSaving = updateMilestoneMutation.isPending && updateMilestoneMutation.variables?.milestoneId === milestone.id;

              return (
                <form
                  key={milestone.id}
                  className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    updateMilestoneMutation.mutate({
                      milestoneId: milestone.id,
                      payload: buildMilestonePayload(form),
                    });
                  }}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-foreground">{milestone.label}</h3>
                    <Badge tone={milestone.is_complete ? "success" : blockers.length ? "warning" : "muted"}>
                      {milestone.is_complete ? "Complete" : blockers.length ? "Blocked" : "Open"}
                    </Badge>
                    {milestone.target_date ? <Badge tone="muted">Target {formatDate(milestone.target_date)}</Badge> : null}
                  </div>

                  <p className="mt-3 text-sm text-muted-foreground">
                    {milestone.completed_at
                      ? `${milestone.completed_by_name ?? "Unknown user"} completed this on ${formatDateTime(milestone.completed_at)}.`
                      : "Set the target date, capture launch notes, and mark the milestone complete when the checkpoint is done."}
                  </p>

                  {blockers.length ? (
                    <div className="mt-3 rounded-[1rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                      Blocked by: {blockers.join(", ")}
                    </div>
                  ) : null}

                  <div className="mt-4 grid gap-4 md:grid-cols-[220px_1fr]">
                    <Field label="Target date">
                      <Input
                        disabled={!canManageWorkflow}
                        type="date"
                        value={form.target_date}
                        onChange={(event) =>
                          setMilestoneForms((current) => ({
                            ...current,
                            [milestone.id]: {
                              ...(current[milestone.id] ?? { target_date: milestone.target_date ?? "", notes: milestone.notes ?? "" }),
                              target_date: event.target.value,
                            },
                          }))
                        }
                      />
                    </Field>
                    <Field label="Notes">
                      <Textarea
                        disabled={!canManageWorkflow}
                        value={form.notes}
                        onChange={(event) =>
                          setMilestoneForms((current) => ({
                            ...current,
                            [milestone.id]: {
                              ...(current[milestone.id] ?? { target_date: milestone.target_date ?? "", notes: milestone.notes ?? "" }),
                              notes: event.target.value,
                            },
                          }))
                        }
                      />
                    </Field>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button disabled={!canManageWorkflow || isSaving} type="submit">
                      {isSaving ? "Saving..." : "Save milestone"}
                    </Button>
                    <Button
                      disabled={!canManageWorkflow || isSaving}
                      onClick={() =>
                        updateMilestoneMutation.mutate({
                          milestoneId: milestone.id,
                          payload: buildMilestonePayload(form, { is_complete: !milestone.is_complete }),
                        })
                      }
                      type="button"
                      variant={milestone.is_complete ? "ghost" : "secondary"}
                    >
                      {milestone.is_complete ? "Mark incomplete" : "Mark complete"}
                    </Button>
                  </div>
                </form>
              );
            })}
          </div>
        </Card>

        <Card className="scroll-mt-24 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="campaign-dependencies">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Dependency map</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Blocked states and prerequisites</h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="muted">{overview.dependencies.length} total</Badge>
              {unresolvedDependencies.length ? <Badge tone="warning">{unresolvedDependencies.length} unresolved</Badge> : null}
              {blockedDraftCount(blockedDraftReasons) ? (
                <Badge tone="warning">{blockedDraftCount(blockedDraftReasons)} draft blockers</Badge>
              ) : null}
            </div>
          </div>

          <div className="mt-4 rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
            <p className="text-sm leading-6 text-muted-foreground">
              Link milestone checkpoints or specific draft stages together so the workspace can show when work is blocked. Draft cards already surface these blockers inside the planner board and list views.
            </p>
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              const dependentNode = parseDependencyNode(dependencyForm.dependent_node);
              const blockerNode = parseDependencyNode(dependencyForm.blocker_node);

              if (!dependentNode || !blockerNode) {
                return;
              }

              createDependencyMutation.mutate({
                dependent_type: dependentNode.type,
                dependent_milestone_id: dependentNode.type === "campaign_milestone" ? dependentNode.milestoneId : null,
                dependent_draft_id: dependentNode.type === "draft_stage" ? dependentNode.draftId : null,
                dependent_stage_key: dependentNode.type === "draft_stage" ? dependentNode.stageKey : null,
                blocker_type: blockerNode.type,
                blocker_milestone_id: blockerNode.type === "campaign_milestone" ? blockerNode.milestoneId : null,
                blocker_draft_id: blockerNode.type === "draft_stage" ? blockerNode.draftId : null,
                blocker_stage_key: blockerNode.type === "draft_stage" ? blockerNode.stageKey : null,
                note: dependencyForm.note.trim() || null,
              });
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Blocked step">
                <Select
                  disabled={!canManageWorkflow}
                  value={dependencyForm.dependent_node}
                  onChange={(event) =>
                    setDependencyForm((current) => ({
                      ...current,
                      dependent_node: event.target.value,
                    }))
                  }
                >
                  <option value="">Select a milestone or draft stage</option>
                  {dependencyNodeOptions.map((option) => (
                    <option key={`dependent-${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Depends on">
                <Select
                  disabled={!canManageWorkflow}
                  value={dependencyForm.blocker_node}
                  onChange={(event) =>
                    setDependencyForm((current) => ({
                      ...current,
                      blocker_node: event.target.value,
                    }))
                  }
                >
                  <option value="">Select a prerequisite step</option>
                  {dependencyNodeOptions.map((option) => (
                    <option key={`blocker-${option.value}`} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            <Field label="Notes">
              <Textarea
                disabled={!canManageWorkflow}
                placeholder="Explain why this dependency exists or what must be finished first."
                value={dependencyForm.note}
                onChange={(event) =>
                  setDependencyForm((current) => ({
                    ...current,
                    note: event.target.value,
                  }))
                }
              />
            </Field>

            <MutationFeedback error={createDependencyMutation.error || deleteDependencyMutation.error} />

            <Button
              disabled={
                !canManageWorkflow ||
                createDependencyMutation.isPending ||
                !dependencyForm.dependent_node ||
                !dependencyForm.blocker_node
              }
              type="submit"
            >
              {createDependencyMutation.isPending ? "Saving..." : "Add dependency"}
            </Button>
          </form>

          <div className="mt-6 space-y-3">
            {overview.dependencies.length ? (
              [...overview.dependencies]
                .sort((left, right) => Number(left.is_satisfied) - Number(right.is_satisfied) || left.dependent_label.localeCompare(right.dependent_label))
                .map((dependency) => (
                  <div key={dependency.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-base font-semibold text-foreground">{dependency.dependent_label}</h3>
                          <Badge tone={dependency.is_satisfied ? "success" : "warning"}>
                            {dependency.is_satisfied ? "Satisfied" : "Blocking"}
                          </Badge>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">Depends on {dependency.blocker_label}</p>
                        {dependency.note ? <p className="mt-3 text-sm leading-6 text-foreground">{dependency.note}</p> : null}
                        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                          {dependency.creator_name ?? "Unknown user"} · Added {formatDateTime(dependency.created_at)}
                        </p>
                      </div>
                      {canManageWorkflow ? (
                        <Button
                          disabled={deleteDependencyMutation.isPending}
                          onClick={() => deleteDependencyMutation.mutate(dependency.id)}
                          type="button"
                          variant="danger"
                        >
                          Delete
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ))
            ) : (
              <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                No dependencies yet. Add one when milestone or draft-stage work should wait on another campaign step.
              </p>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <Card className="scroll-mt-24 border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="campaign-assets">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Asset library</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign assets</h2>
            </div>
            <Badge tone="muted">{overview.assets.length} items</Badge>
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              saveAssetMutation.mutate();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Asset name">
                <Input
                  value={assetForm.name}
                  onChange={(event) => setAssetForm((current) => ({ ...current, name: event.target.value }))}
                />
              </Field>
              <Field label="Asset type">
                <Input
                  placeholder="Image, video, brief, deck"
                  value={assetForm.asset_type}
                  onChange={(event) => setAssetForm((current) => ({ ...current, asset_type: event.target.value }))}
                />
              </Field>
            </div>

            <Field label="File URL">
              <Input
                value={assetForm.file_url}
                onChange={(event) => setAssetForm((current) => ({ ...current, file_url: event.target.value }))}
              />
            </Field>

            <div className="grid gap-4 md:grid-cols-3">
              <Field label="Thumbnail URL">
                <Input
                  value={assetForm.thumbnail_url}
                  onChange={(event) => setAssetForm((current) => ({ ...current, thumbnail_url: event.target.value }))}
                />
              </Field>
              <Field label="Mime type">
                <Input
                  placeholder="image/png"
                  value={assetForm.mime_type}
                  onChange={(event) => setAssetForm((current) => ({ ...current, mime_type: event.target.value }))}
                />
              </Field>
              <Field label="File size (bytes)">
                <Input
                  inputMode="numeric"
                  value={assetForm.file_size_bytes}
                  onChange={(event) => setAssetForm((current) => ({ ...current, file_size_bytes: event.target.value }))}
                />
              </Field>
            </div>

            <Field label="Notes">
              <Textarea
                className="min-h-[100px]"
                value={assetForm.notes}
                onChange={(event) => setAssetForm((current) => ({ ...current, notes: event.target.value }))}
              />
            </Field>

            <MutationFeedback error={saveAssetMutation.error || deleteAssetMutation.error} />
            <div className="flex flex-wrap gap-3">
              <Button disabled={saveAssetMutation.isPending} type="submit">
                {saveAssetMutation.isPending ? "Saving..." : editingAssetId ? "Update asset" : "Add asset"}
              </Button>
              {editingAssetId ? (
                <Button
                  onClick={() => {
                    setEditingAssetId(null);
                    setAssetForm(emptyAssetForm);
                  }}
                  type="button"
                  variant="ghost"
                >
                  Cancel edit
                </Button>
              ) : null}
            </div>
          </form>

          <div className="mt-6 space-y-3">
            {overview.assets.length ? (
              overview.assets.map((asset) => (
                <div key={asset.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base font-semibold">{asset.name}</h3>
                      <Badge>{asset.asset_type}</Badge>
                      {asset.mime_type ? <Badge tone="muted">{asset.mime_type}</Badge> : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => {
                          setEditingAssetId(asset.id);
                          setAssetForm(toAssetForm(asset));
                        }}
                        type="button"
                        variant="secondary"
                      >
                        Edit
                      </Button>
                      <Button
                        disabled={deleteAssetMutation.isPending}
                        onClick={() => {
                          if (window.confirm(`Delete ${asset.name}?`)) {
                            deleteAssetMutation.mutate(asset.id);
                          }
                        }}
                        type="button"
                        variant="danger"
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                    <a className="font-medium text-primary" href={asset.file_url} rel="noreferrer" target="_blank">
                      Open asset
                    </a>
                    {asset.thumbnail_url ? (
                      <a className="font-medium text-primary" href={asset.thumbnail_url} rel="noreferrer" target="_blank">
                        Preview
                      </a>
                    ) : null}
                    {asset.file_size_bytes ? <span>{formatFileSize(asset.file_size_bytes)}</span> : null}
                  </div>
                  {asset.notes ? <p className="mt-3 text-sm leading-6 text-foreground">{asset.notes}</p> : null}
                  <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {asset.creator_name ?? "Unknown user"} · Updated {formatDateTime(asset.updated_at)}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                Add campaign links, working files, or reference assets to build a reusable library here.
              </p>
            )}
          </div>
        </Card>

        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Version feed</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Recent draft snapshots</h2>
            </div>
            <Badge tone="muted">{overview.recent_versions.length} saved</Badge>
          </div>

          <div className="mt-5 space-y-3">
            {overview.recent_versions.length ? (
              overview.recent_versions.map((version) => (
                <Link
                  key={version.id}
                  className="block rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 transition hover:bg-white"
                  to={`/drafts/${version.draft_id}`}
                >
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="text-base font-semibold">{version.draft_title}</h3>
                    <Badge tone="muted">v{version.version_number}</Badge>
                    <Badge>{version.platform}</Badge>
                    <Badge tone={statusTone(version.status_type)}>
                      {formatStatusLabel(version.status, version.status_label)}
                    </Badge>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">{version.change_summary ?? version.content_type}</p>
                  <p className="mt-3 text-sm text-muted-foreground">
                    {version.creator_name ?? "Unknown user"} · {formatDateTime(version.created_at)}
                  </p>
                </Link>
              ))
            ) : (
              <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                Version history will appear here once draft edits begin creating snapshots.
              </p>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <ThreadedCommentsCard
          comments={commentsQuery.data ?? []}
          description="Keep campaign-level planning and coordination in a threaded discussion that sits beside the activity feed."
          emptyMessage="No campaign discussion yet. Start the first thread here."
          error={commentMutation.error || commentsQuery.error}
          eyebrow="Discussion"
          isLoading={commentsQuery.isLoading}
          isSubmitting={commentMutation.isPending}
          onCreate={(payload) => commentMutation.mutateAsync(payload)}
          placeholder="Add a campaign comment. Use @email for mentions and reply inline to keep planning threads organized."
          title="Campaign discussion"
        />

        <AssignmentPanel
          assignmentTypeOptions={["campaign"]}
          assignments={assignmentsQuery.data ?? []}
          currentUserId={currentUser?.id}
          defaultAssignmentType="campaign"
          description="Assign campaign-level ownership without leaving the workspace."
          emptyMessage="Campaign assignments will appear here when work is delegated."
          error={createAssignmentMutation.error || completeAssignmentMutation.error || assignmentsQuery.error}
          eyebrow="Assignments"
          isCompletingId={completeAssignmentMutation.variables ?? null}
          isCreating={createAssignmentMutation.isPending}
          isLoading={assignmentsQuery.isLoading}
          memberError={membershipsQuery.error}
          members={membershipsQuery.data ?? []}
          onComplete={(assignmentId) => completeAssignmentMutation.mutate(assignmentId)}
          onCreate={(payload) => createAssignmentMutation.mutateAsync(payload)}
          title="Campaign ownership"
        />
      </div>

      <div className="mt-8 scroll-mt-24" id="campaign-planner">
        <CampaignPlanner
          currentUserRole={currentMembership?.role}
          dependencies={overview.dependencies}
          drafts={overview.drafts}
          isMovingDraftId={moveDraftStageMutation.variables?.draft.id ?? null}
          onMoveDraft={(draft, targetStatus) => moveDraftStageMutation.mutate({ draft, targetStatus })}
          planningSummary={overview.planning_summary}
          schedule={overview.schedule}
          workflow={overview.draft_workflow}
        />
        {moveDraftStageMutation.error ? (
          <div className="mt-4">
            <MutationFeedback error={moveDraftStageMutation.error} />
          </div>
        ) : null}
      </div>

      <div className="mt-8">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Campaign activity</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Collaboration feed</h2>
            </div>
            <Badge tone="muted">{overview.activity_timeline.length} events</Badge>
          </div>

          <div className="mt-5 space-y-3">
            {overview.activity_timeline.length ? (
              overview.activity_timeline.map((item) => {
                const activity = describeActivity(item);
                const href = activityHref(item);

                return (
                  <div key={item.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge>{item.entity_type}</Badge>
                      <p className="text-sm font-medium text-foreground">{activity.title}</p>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {item.actor_name ?? "Unknown user"} · {formatDateTime(item.created_at)}
                    </p>
                    {activity.detail ? <p className="mt-3 text-sm leading-6 text-foreground">{activity.detail}</p> : null}
                    {href ? (
                      <Link className="mt-4 inline-flex text-sm font-medium text-primary" to={href}>
                        Open linked item
                      </Link>
                    ) : null}
                  </div>
                );
              })
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

function WorkspaceSummaryCard({
  hint,
  label,
  value,
}: {
  hint: string;
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">{hint}</p>
    </div>
  );
}

function QuickAction({ href, label }: { href: string; label: string }) {
  return (
    <a
      className="block rounded-[1.15rem] border border-border bg-muted/40 px-4 py-3 text-sm font-medium text-foreground transition hover:bg-white"
      href={href}
    >
      {label}
    </a>
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

function toAssetForm(asset: CampaignAsset): AssetFormState {
  return {
    name: asset.name,
    asset_type: asset.asset_type,
    file_url: asset.file_url,
    thumbnail_url: asset.thumbnail_url ?? "",
    mime_type: asset.mime_type ?? "",
    file_size_bytes: asset.file_size_bytes ? String(asset.file_size_bytes) : "",
    notes: asset.notes ?? "",
  };
}

function formatFileSize(value: number) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function describeActivity(item: AuditLog) {
  switch (item.action) {
    case "campaign.comment_created":
      return {
        title: "Campaign discussion updated",
        detail: metadataNumber(item.metadata, "parent_comment_id")
          ? "A reply was added in the campaign thread."
          : "A new campaign thread was started.",
      };
    case "draft.comment_created":
      return {
        title: "Draft discussion updated",
        detail: `Draft #${metadataNumber(item.metadata, "draft_id") ?? item.entity_id} received a threaded comment.`,
      };
    case "draft.submitted_for_review":
      return {
        title: "Draft submitted for review",
        detail: `Draft #${metadataNumber(item.metadata, "draft_id") ?? item.entity_id} moved into review.`,
      };
    case "draft.review_commented":
      return {
        title: "Review note added",
        detail: `Draft #${metadataNumber(item.metadata, "draft_id") ?? item.entity_id} received reviewer feedback.`,
      };
    case "draft.review_approved":
      return {
        title: "Draft approved",
        detail: `Draft #${metadataNumber(item.metadata, "draft_id") ?? item.entity_id} was approved.`,
      };
    case "draft.review_rejected":
      return {
        title: "Draft rejected",
        detail: `Draft #${metadataNumber(item.metadata, "draft_id") ?? item.entity_id} was rejected and sent back for edits.`,
      };
    case "draft.resubmitted_for_review":
      return {
        title: "Draft resubmitted",
        detail: `Version ${metadataNumber(item.metadata, "version_number") ?? "next"} returned to review.`,
      };
    case "assignment.created":
      return {
        title: "Assignment created",
        detail: `${formatStatusLabel(String(item.metadata.assignment_type ?? "assignment"))} ownership was added.`,
      };
    case "assignment.updated":
      return {
        title: "Assignment updated",
        detail: `${formatStatusLabel(String(item.metadata.assignment_type ?? "assignment"))} ownership changed status.`,
      };
    default:
      return {
        title: formatActionLabel(item.action),
        detail: null,
      };
  }
}

function activityHref(item: AuditLog) {
  const draftId = metadataNumber(item.metadata, "draft_id");
  const campaignId = metadataNumber(item.metadata, "campaign_id");

  if (draftId) {
    return `/drafts/${draftId}`;
  }
  if (campaignId) {
    return `/campaigns/${campaignId}`;
  }
  if (item.entity_type === "campaign") {
    return `/campaigns/${item.entity_id}`;
  }
  return null;
}

function metadataNumber(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string" && value) {
    return Number(value);
  }
  return null;
}

function buildEmptyDraftForm(initialStatus: DraftStatus): DraftFormState {
  return {
    title: "",
    platform: "",
    content_type: "",
    content_body: "",
    status: initialStatus,
    planned_publish_at: "",
  };
}

function buildMilestonePayload(form: MilestoneFormState | undefined, overrides: Partial<{ is_complete: boolean }> = {}) {
  return {
    target_date: form?.target_date || null,
    notes: form?.notes.trim() || null,
    ...overrides,
  };
}

function buildDraftBlockerMap(dependencies: CampaignDependency[]) {
  return dependencies.reduce<Record<number, string[]>>((accumulator, dependency) => {
    if (dependency.dependent_type !== "draft_stage" || !dependency.dependent_draft_id) {
      return accumulator;
    }

    accumulator[dependency.dependent_draft_id] = [
      ...(accumulator[dependency.dependent_draft_id] ?? []),
      dependency.blocker_label,
    ];
    return accumulator;
  }, {});
}

function buildMilestoneBlockerMap(dependencies: CampaignDependency[]) {
  return dependencies.reduce<Record<number, string[]>>((accumulator, dependency) => {
    if (dependency.dependent_type !== "campaign_milestone" || !dependency.dependent_milestone_id) {
      return accumulator;
    }

    accumulator[dependency.dependent_milestone_id] = [
      ...(accumulator[dependency.dependent_milestone_id] ?? []),
      dependency.blocker_label,
    ];
    return accumulator;
  }, {});
}

function blockedMilestoneCount(blockedMilestoneReasons: Record<number, string[]>) {
  return Object.keys(blockedMilestoneReasons).length;
}

function blockedDraftCount(blockedDraftReasons: Record<number, string[]>) {
  return Object.keys(blockedDraftReasons).length;
}

function buildDependencyNodeOptions({
  drafts,
  milestones,
  workflow,
}: {
  drafts: ContentDraft[];
  milestones: CampaignMilestone[];
  workflow: CampaignOverview["draft_workflow"];
}): DependencyNodeOption[] {
  return [
    ...milestones.map((milestone) => ({
      value: `campaign_milestone:${milestone.id}`,
      label: `Milestone · ${milestone.label}`,
    })),
    ...drafts.flatMap((draft) =>
      workflow.stages.map((stage) => ({
        value: `draft_stage:${draft.id}:${stage.key}`,
        label: `Draft · ${draft.title} -> ${stage.label}`,
      })),
    ),
  ];
}

function parseDependencyNode(value: string) {
  const [type, entityId, stageKey] = value.split(":");
  const parsedId = Number(entityId);

  if (!type || !Number.isFinite(parsedId)) {
    return null;
  }

  if (type === "campaign_milestone") {
    return {
      type,
      milestoneId: parsedId,
    } as const;
  }

  if (type === "draft_stage" && stageKey) {
    return {
      type,
      draftId: parsedId,
      stageKey,
    } as const;
  }

  return null;
}

function statusTone(statusType: ContentDraft["status_type"]) {
  switch (statusType) {
    case "review":
    case "changes_requested":
      return "warning";
    case "approved":
    case "scheduled":
    case "published":
      return "success";
    default:
      return "muted";
  }
}
