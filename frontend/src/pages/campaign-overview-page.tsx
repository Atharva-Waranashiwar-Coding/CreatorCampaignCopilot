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
  CampaignOverview,
  CollaborationComment,
  ContentDraft,
  DraftStatus,
  Membership,
} from "../lib/types";

const draftStatuses: DraftStatus[] = ["idea", "draft", "in_review"];

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

const emptyAssetForm: AssetFormState = {
  name: "",
  asset_type: "",
  file_url: "",
  thumbnail_url: "",
  mime_type: "",
  file_size_bytes: "",
  notes: "",
};

export function CampaignOverviewPage() {
  const { campaignId } = useParams();
  const token = useAuthStore((state) => state.token);
  const currentUser = useAuthStore((state) => state.user);
  const [briefForm, setBriefForm] = useState<BriefFormState>(emptyBriefForm);
  const [draftForm, setDraftForm] = useState<DraftFormState>(emptyDraftForm);
  const [assetForm, setAssetForm] = useState<AssetFormState>(emptyAssetForm);
  const [editingAssetId, setEditingAssetId] = useState<number | null>(null);

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
      setDraftForm(emptyDraftForm);
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

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Drafts" value={overview.drafts.length} />
        <MetricCard label="Assets" value={overview.assets.length} />
        <MetricCard label="Scheduled" value={overview.schedule.length} />
        <MetricCard label="Brief" value={overview.brief ? "Ready" : "Missing"} />
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

          <div className="mt-4 rounded-[1.25rem] border border-border bg-white/80 p-4">
            <p className="text-sm text-muted-foreground">{campaign.objective ?? "Objective not set yet."}</p>
            <p className="mt-2 text-sm text-muted-foreground">{campaign.audience ?? "Audience not set yet."}</p>
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
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
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
                    <Badge tone={version.status === "approved" || version.status === "published" ? "success" : version.status === "rejected" || version.status === "in_review" ? "warning" : "muted"}>
                      {formatStatusLabel(version.status)}
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

      <div className="mt-8">
        <CampaignPlanner
          currentUserRole={currentMembership?.role}
          drafts={overview.drafts}
          isMovingDraftId={moveDraftStageMutation.variables?.draft.id ?? null}
          onMoveDraft={(draft, targetStatus) => moveDraftStageMutation.mutate({ draft, targetStatus })}
          planningSummary={overview.planning_summary}
          schedule={overview.schedule}
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
