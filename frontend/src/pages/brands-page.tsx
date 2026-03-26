import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

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
import { cn } from "../lib/cn";
import { formatDateTime } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { AuditLog, Brand, BrandRole, DraftStageType, DraftWorkflowStage, Membership } from "../lib/types";

const roleOptions: BrandRole[] = ["owner", "admin", "editor", "reviewer", "viewer"];
const workflowStageTypeOptions: DraftStageType[] = [
  "backlog",
  "in_progress",
  "review",
  "approved",
  "scheduled",
  "published",
  "changes_requested",
];
const workflowColorOptions = ["amber", "sky", "emerald", "cyan", "rose", "slate", "orange", "blue"];

type BrandFormState = {
  name: string;
  slug: string;
  description: string;
  industry: string;
  preferred_channels: string;
  guidelines_summary: string;
};

const emptyBrandForm: BrandFormState = {
  name: "",
  slug: "",
  description: "",
  industry: "",
  preferred_channels: "",
  guidelines_summary: "",
};

export function BrandsPage() {
  const token = useAuthStore((state) => state.token);
  const [selectedBrandId, setSelectedBrandId] = useState<number | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState<BrandFormState>(emptyBrandForm);
  const [editForm, setEditForm] = useState<BrandFormState>(emptyBrandForm);
  const [workflowStages, setWorkflowStages] = useState<DraftWorkflowStage[]>([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<BrandRole>("editor");

  const brandsQuery = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiRequest<Brand[]>("/brands", {}, token),
  });

  const selectedBrand = useMemo(
    () => brandsQuery.data?.find((brand) => brand.id === selectedBrandId) ?? null,
    [brandsQuery.data, selectedBrandId],
  );

  useEffect(() => {
    if (!brandsQuery.data?.length) {
      setSelectedBrandId(null);
      setEditForm(emptyBrandForm);
      setWorkflowStages([]);
      return;
    }

    if (!selectedBrandId || !brandsQuery.data.some((brand) => brand.id === selectedBrandId)) {
      setSelectedBrandId(brandsQuery.data[0].id);
      return;
    }

    if (selectedBrand) {
      setEditForm({
        name: selectedBrand.name,
        slug: selectedBrand.slug,
        description: selectedBrand.description ?? "",
        industry: selectedBrand.industry ?? "",
        preferred_channels: selectedBrand.preferred_channels.join(", "),
        guidelines_summary: selectedBrand.guidelines_summary ?? "",
      });
      setWorkflowStages(selectedBrand.draft_workflow.stages);
    }
  }, [brandsQuery.data, selectedBrand, selectedBrandId]);

  const membershipsQuery = useQuery({
    queryKey: ["brand-memberships", selectedBrandId],
    queryFn: () => apiRequest<Membership[]>(`/brands/${selectedBrandId}/memberships`, {}, token),
    enabled: Boolean(selectedBrandId),
  });

  const auditQuery = useQuery({
    queryKey: ["brand-audit-logs", selectedBrandId],
    queryFn: () => apiRequest<AuditLog[]>(`/brands/${selectedBrandId}/audit-logs`, {}, token),
    enabled: Boolean(selectedBrandId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: BrandFormState) =>
      apiRequest<Brand>(
        "/brands",
        {
          method: "POST",
          body: JSON.stringify({
            ...payload,
            preferred_channels: splitChannels(payload.preferred_channels),
            slug: payload.slug || undefined,
          }),
        },
        token,
      ),
    onSuccess: (brand) => {
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      setSelectedBrandId(brand.id);
      setCreateForm(emptyBrandForm);
      setIsCreateOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: BrandFormState) =>
      apiRequest<Brand>(
        `/brands/${selectedBrandId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            ...payload,
            preferred_channels: splitChannels(payload.preferred_channels),
          }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () =>
      apiRequest<void>(
        `/brands/${selectedBrandId}`,
        {
          method: "DELETE",
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      apiRequest<Membership>(
        `/brands/${selectedBrandId}/memberships`,
        {
          method: "POST",
          body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brand-memberships", selectedBrandId] });
      queryClient.invalidateQueries({ queryKey: ["brand-audit-logs", selectedBrandId] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      setInviteEmail("");
      setInviteRole("editor");
    },
  });

  const workflowMutation = useMutation({
    mutationFn: (stages: DraftWorkflowStage[]) =>
      apiRequest<Brand>(
        `/brands/${selectedBrandId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            draft_workflow: {
              stages: stages.map((stage) => ({
                key: stage.key,
                label: stage.label,
                stage_type: stage.stage_type,
                color: stage.color,
                description: stage.description,
                is_initial: stage.is_initial,
                allowed_next_stage_keys: stage.allowed_next_stage_keys,
              })),
            },
          }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      queryClient.invalidateQueries({ queryKey: ["campaign-overview"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-analytics"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });

  const brandCount = brandsQuery.data?.length ?? 0;
  const ownedBrandCount = brandsQuery.data?.filter((brand) => brand.current_user_role === "owner").length ?? 0;
  const selectedBrandMembershipCount = membershipsQuery.data?.length ?? selectedBrand?.membership_count ?? 0;
  const selectedBrandAuditCount = auditQuery.data?.length ?? 0;

  const jumpToSection = (sectionId: string) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="min-w-0">
      <PageHeader
        eyebrow="Brands"
        title="Brands and roles"
        description="Switch brands fast, change the rules that matter, and manage team access without hunting through split panels."
        actions={
          <Button onClick={() => setIsCreateOpen((current) => !current)} variant={isCreateOpen ? "secondary" : "primary"}>
            {isCreateOpen ? "Close create panel" : "Create brand"}
          </Button>
        }
      />

      <div className="space-y-6">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Brand control center</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 md:text-[2.15rem]">
                Keep switching light. Open detail only when you need it.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
                The page now flows from overview to detail: create only when needed, pick a brand from the switcher, then work through profile, workflow, team, and audit in one pass.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <SummaryPill label="Brands" value={brandCount} />
              <SummaryPill label="Owned" value={ownedBrandCount} />
              <SummaryPill
                label="Open panel"
                value={isCreateOpen ? "create" : selectedBrand ? "editing" : "idle"}
              />
            </div>
          </div>

          {isCreateOpen ? (
            <div className="mt-6 rounded-[1.5rem] border border-primary/15 bg-[linear-gradient(180deg,rgba(15,118,135,0.05),rgba(255,255,255,0.92))] p-5 md:p-6">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">New brand</p>
                  <h3 className="mt-2 text-xl font-semibold tracking-tight">Create a brand without leaving the page</h3>
                </div>
                <Button onClick={() => setIsCreateOpen(false)} type="button" variant="ghost">
                  Hide panel
                </Button>
              </div>

              <form
                className="mt-5 grid gap-4 lg:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  createMutation.mutate(createForm);
                }}
              >
                <Field label="Brand name">
                  <Input
                    value={createForm.name}
                    onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
                  />
                </Field>
                <Field label="Slug">
                  <Input
                    placeholder="optional-custom-slug"
                    value={createForm.slug}
                    onChange={(event) => setCreateForm((current) => ({ ...current, slug: event.target.value }))}
                  />
                </Field>
                <Field label="Industry">
                  <Input
                    value={createForm.industry}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, industry: event.target.value }))
                    }
                  />
                </Field>
                <Field label="Preferred channels">
                  <Input
                    placeholder="LinkedIn, Instagram, Email"
                    value={createForm.preferred_channels}
                    onChange={(event) =>
                      setCreateForm((current) => ({
                        ...current,
                        preferred_channels: event.target.value,
                      }))
                    }
                  />
                </Field>
                <Field className="lg:col-span-2" label="Description">
                  <Textarea
                    value={createForm.description}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, description: event.target.value }))
                    }
                  />
                </Field>
                <Field className="lg:col-span-2" label="Guidelines summary">
                  <Textarea
                    value={createForm.guidelines_summary}
                    onChange={(event) =>
                      setCreateForm((current) => ({
                        ...current,
                        guidelines_summary: event.target.value,
                      }))
                    }
                  />
                </Field>

                <div className="lg:col-span-2">
                  <MutationFeedback error={createMutation.error} />
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button disabled={createMutation.isPending} type="submit">
                      {createMutation.isPending ? "Creating..." : "Create brand"}
                    </Button>
                    <Button
                      onClick={() => {
                        setCreateForm(emptyBrandForm);
                        setIsCreateOpen(false);
                      }}
                      type="button"
                      variant="secondary"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </form>
            </div>
          ) : null}
        </Card>

        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Brand switcher</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Your brands</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                Scan the essentials here, then open one brand at a time below. No empty companion column, no split attention.
              </p>
            </div>
            <Badge tone="muted">{brandCount} total</Badge>
          </div>

          <div className="mt-6">
            {brandsQuery.data?.length ? (
              <div className="flex gap-4 overflow-x-auto pb-2">
                {brandsQuery.data.map((brand) => (
                  <button
                    key={brand.id}
                    className={cn(
                      "min-w-[18rem] max-w-[22rem] shrink-0 rounded-[1.5rem] border px-5 py-5 text-left transition",
                      "shadow-[0_12px_36px_-30px_rgba(15,23,42,0.45)]",
                      selectedBrandId === brand.id
                        ? "border-primary bg-[linear-gradient(180deg,rgba(15,118,135,0.1),rgba(255,255,255,0.98))]"
                        : "border-border bg-white/85 hover:border-primary/30 hover:bg-white",
                    )}
                    onClick={() => setSelectedBrandId(brand.id)}
                    type="button"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <Badge tone={selectedBrandId === brand.id ? "default" : "muted"}>
                        {selectedBrandId === brand.id ? "Selected" : "Open"}
                      </Badge>
                      <Badge>{brand.current_user_role}</Badge>
                    </div>

                    <h3 className="mt-4 text-lg font-semibold tracking-tight text-slate-950">{brand.name}</h3>
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">
                      {brand.description ?? "Add a short description so teammates know what this brand is trying to do."}
                    </p>

                    <div className="mt-4 flex flex-wrap gap-2">
                      {brand.preferred_channels.slice(0, 3).map((channel) => (
                        <Badge key={channel} tone="muted">
                          {channel}
                        </Badge>
                      ))}
                    </div>

                    <div className="mt-5 grid grid-cols-3 gap-3 rounded-[1.25rem] border border-slate-200/80 bg-white/80 px-3 py-3 text-center">
                      <MiniCount label="Members" value={brand.membership_count} />
                      <MiniCount label="Projects" value={brand.project_count} />
                      <MiniCount label="Campaigns" value={brand.campaign_count} />
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-[1.5rem] border border-dashed border-border bg-white/60 px-4 py-10 text-center">
                <p className="text-base font-semibold text-slate-950">No brands yet</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  Open the create panel and add the first brand to unlock projects, campaigns, workflows, and memberships.
                </p>
              </div>
            )}
          </div>
        </Card>

        {selectedBrand ? (
          <div className="space-y-6">
            <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                <div className="max-w-3xl">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{selectedBrand.current_user_role}</Badge>
                    <Badge tone="muted">Updated {formatDateTime(selectedBrand.updated_at)}</Badge>
                  </div>
                  <h2 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950">{selectedBrand.name}</h2>
                  <p className="mt-3 text-sm leading-6 text-muted-foreground md:text-base">
                    {selectedBrand.description ??
                      "Use the profile section below to set a clear description, channel focus, and brand guidance."}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    {(selectedBrand.preferred_channels.length ? selectedBrand.preferred_channels : ["No channels set"]).map(
                      (channel) => (
                        <Badge key={channel} tone="muted">
                          {channel}
                        </Badge>
                      ),
                    )}
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[23rem] xl:grid-cols-2">
                  <SummaryPill label="Members" value={selectedBrandMembershipCount} />
                  <SummaryPill label="Workflow stages" value={workflowStages.length} />
                  <SummaryPill label="Projects" value={selectedBrand.project_count} />
                  <SummaryPill label="Activity" value={selectedBrandAuditCount} />
                </div>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                <SectionJumpButton label="Profile" onClick={() => jumpToSection("brand-profile")} />
                <SectionJumpButton label="Workflow" onClick={() => jumpToSection("brand-workflow")} />
                <SectionJumpButton label="Team" onClick={() => jumpToSection("brand-team")} />
                <SectionJumpButton label="Activity" onClick={() => jumpToSection("brand-activity")} />
              </div>
            </Card>

            <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="brand-profile">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Profile</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Brand settings</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                    Keep the essentials together: name, slug, industry, channels, and the guidance teammates need before they draft.
                  </p>
                </div>
                {selectedBrand.current_user_role === "owner" ? (
                  <Button
                    disabled={deleteMutation.isPending}
                    onClick={() => {
                      if (window.confirm(`Delete ${selectedBrand.name}? This removes its projects and campaigns.`)) {
                        deleteMutation.mutate();
                      }
                    }}
                    type="button"
                    variant="danger"
                  >
                    {deleteMutation.isPending ? "Deleting..." : "Delete brand"}
                  </Button>
                ) : null}
              </div>

              <form
                className="mt-6 grid gap-4 lg:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault();
                  updateMutation.mutate(editForm);
                }}
              >
                <Field label="Brand name">
                  <Input
                    value={editForm.name}
                    onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))}
                  />
                </Field>
                <Field label="Slug">
                  <Input
                    value={editForm.slug}
                    onChange={(event) => setEditForm((current) => ({ ...current, slug: event.target.value }))}
                  />
                </Field>
                <Field label="Industry">
                  <Input
                    value={editForm.industry}
                    onChange={(event) =>
                      setEditForm((current) => ({ ...current, industry: event.target.value }))
                    }
                  />
                </Field>
                <Field label="Preferred channels">
                  <Input
                    value={editForm.preferred_channels}
                    onChange={(event) =>
                      setEditForm((current) => ({
                        ...current,
                        preferred_channels: event.target.value,
                      }))
                    }
                  />
                </Field>
                <Field className="lg:col-span-2" label="Description">
                  <Textarea
                    value={editForm.description}
                    onChange={(event) =>
                      setEditForm((current) => ({
                        ...current,
                        description: event.target.value,
                      }))
                    }
                  />
                </Field>
                <Field className="lg:col-span-2" label="Guidelines summary">
                  <Textarea
                    value={editForm.guidelines_summary}
                    onChange={(event) =>
                      setEditForm((current) => ({
                        ...current,
                        guidelines_summary: event.target.value,
                      }))
                    }
                  />
                </Field>

                <div className="lg:col-span-2">
                  <MutationFeedback error={updateMutation.error} />
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button disabled={updateMutation.isPending} type="submit" variant="primary">
                      {updateMutation.isPending ? "Saving..." : "Save changes"}
                    </Button>
                  </div>
                </div>
              </form>
            </Card>

            <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="brand-workflow">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Workflow</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Custom lifecycle stages</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                    Drafts move through these stages. Keep the flow readable, set a clear starting point, and decide exactly where each stage can lead.
                  </p>
                </div>
                <Badge tone="muted">{workflowStages.length} stages</Badge>
              </div>

              <div className="mt-6 flex flex-wrap gap-2">
                {workflowStages.map((stage, index) => (
                  <div
                    key={stage.key}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-2 text-sm text-slate-700"
                  >
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {index + 1}
                    </span>
                    <span className="font-medium">{stage.label}</span>
                  </div>
                ))}
              </div>

              <div className="mt-6 space-y-4">
                {workflowStages.map((stage, index) => (
                  <div key={stage.key} className="rounded-[1.4rem] border border-border bg-white/80 p-5">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Stage key</p>
                        <p className="mt-2 text-sm font-medium">{stage.key}</p>
                      </div>
                      <Button
                        disabled={workflowStages.length <= 4}
                        onClick={() =>
                          setWorkflowStages((current) => current.filter((item) => item.key !== stage.key))
                        }
                        type="button"
                        variant="ghost"
                      >
                        Remove
                      </Button>
                    </div>

                    <div className="mt-4 grid gap-4 lg:grid-cols-3">
                      <Field label="Label">
                        <Input
                          value={stage.label}
                          onChange={(event) =>
                            setWorkflowStages((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index ? { ...item, label: event.target.value } : item,
                              ),
                            )
                          }
                        />
                      </Field>
                      <Field label="Stage type">
                        <Select
                          value={stage.stage_type}
                          onChange={(event) =>
                            setWorkflowStages((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index
                                  ? { ...item, stage_type: event.target.value as DraftStageType }
                                  : item,
                              ),
                            )
                          }
                        >
                          {workflowStageTypeOptions.map((stageType) => (
                            <option key={stageType} value={stageType}>
                              {stageType.replace(/_/g, " ")}
                            </option>
                          ))}
                        </Select>
                      </Field>
                      <Field label="Color">
                        <Select
                          value={stage.color}
                          onChange={(event) =>
                            setWorkflowStages((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index ? { ...item, color: event.target.value } : item,
                              ),
                            )
                          }
                        >
                          {workflowColorOptions.map((color) => (
                            <option key={color} value={color}>
                              {color}
                            </option>
                          ))}
                        </Select>
                      </Field>
                      <Field className="lg:col-span-3" label="Description">
                        <Textarea
                          className="min-h-[88px]"
                          value={stage.description ?? ""}
                          onChange={(event) =>
                            setWorkflowStages((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index
                                  ? { ...item, description: event.target.value || null }
                                  : item,
                              ),
                            )
                          }
                        />
                      </Field>
                    </div>

                    <div className="mt-4">
                      <label className="inline-flex items-center gap-2 text-sm text-foreground">
                        <input
                          checked={stage.is_initial}
                          className="h-4 w-4 rounded border-border"
                          onChange={(event) =>
                            setWorkflowStages((current) =>
                              current.map((item, itemIndex) =>
                                itemIndex === index ? { ...item, is_initial: event.target.checked } : item,
                              ),
                            )
                          }
                          type="checkbox"
                        />
                        Allow new drafts to start here
                      </label>
                    </div>

                    <div className="mt-4">
                      <p className="text-sm font-medium text-foreground">Allowed next stages</p>
                      <div className="mt-3 grid gap-2 lg:grid-cols-3">
                        {workflowStages
                          .filter((candidate) => candidate.key !== stage.key)
                          .map((candidate) => (
                            <label key={candidate.key} className="inline-flex items-center gap-2 text-sm text-foreground">
                              <input
                                checked={stage.allowed_next_stage_keys.includes(candidate.key)}
                                className="h-4 w-4 rounded border-border"
                                onChange={() =>
                                  setWorkflowStages((current) =>
                                    current.map((item, itemIndex) =>
                                      itemIndex === index
                                        ? {
                                            ...item,
                                            allowed_next_stage_keys: item.allowed_next_stage_keys.includes(candidate.key)
                                              ? item.allowed_next_stage_keys.filter((key) => key !== candidate.key)
                                              : [...item.allowed_next_stage_keys, candidate.key],
                                          }
                                        : item,
                                    ),
                                  )
                                }
                                type="checkbox"
                              />
                              {candidate.label}
                            </label>
                          ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5">
                <MutationFeedback error={workflowMutation.error} />
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button
                    onClick={() =>
                      setWorkflowStages((current) => [
                        ...current,
                        {
                          key: slugifyStageKey(`stage_${current.length + 1}`),
                          label: `Stage ${current.length + 1}`,
                          stage_type: "in_progress",
                          color: "slate",
                          description: null,
                          is_initial: false,
                          allowed_next_stage_keys: [],
                        },
                      ])
                    }
                    type="button"
                    variant="secondary"
                  >
                    Add stage
                  </Button>
                  <Button
                    disabled={workflowMutation.isPending}
                    onClick={() => workflowMutation.mutate(workflowStages)}
                    type="button"
                  >
                    {workflowMutation.isPending ? "Saving workflow..." : "Save workflow"}
                  </Button>
                </div>
              </div>
            </Card>

            <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="brand-team">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Team</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Members and invites</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                    Invite people fast, keep role labels visible, and review membership status without digging through a side panel.
                  </p>
                </div>
                <Badge tone="muted">{selectedBrandMembershipCount} listed</Badge>
              </div>

              <form
                className="mt-6 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto]"
                onSubmit={(event) => {
                  event.preventDefault();
                  inviteMutation.mutate();
                }}
              >
                <Input
                  placeholder="teammate@brand.com"
                  type="email"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                />
                <Select value={inviteRole} onChange={(event) => setInviteRole(event.target.value as BrandRole)}>
                  {roleOptions.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </Select>
                <Button disabled={inviteMutation.isPending} type="submit">
                  {inviteMutation.isPending ? "Inviting..." : "Invite"}
                </Button>
              </form>

              <div className="mt-4">
                <MutationFeedback error={inviteMutation.error} />
              </div>

              <div className="mt-6 grid gap-3 xl:grid-cols-2">
                {membershipsQuery.data?.length ? (
                  membershipsQuery.data.map((membership) => (
                    <div
                      key={membership.id}
                      className="rounded-[1.35rem] border border-border bg-white/80 px-4 py-4"
                    >
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="text-sm font-medium text-foreground">
                          {membership.user?.full_name ?? membership.invite_email}
                        </p>
                        <Badge>{membership.role}</Badge>
                        <Badge tone={membership.status === "active" ? "success" : "warning"}>
                          {membership.status}
                        </Badge>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">
                        {membership.user?.email ?? membership.invite_email}
                      </p>
                      <p className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                        Invited {formatDateTime(membership.invited_at)}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No memberships created yet.</p>
                )}
              </div>
            </Card>

            <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5" id="brand-activity">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Activity</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">Audit trail</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                    Every change lands here, so you can scan who changed what without opening another page.
                  </p>
                </div>
                <Badge tone="muted">{selectedBrandAuditCount} entries</Badge>
              </div>

              <div className="mt-6 space-y-3">
                {auditQuery.data?.length ? (
                  auditQuery.data.map((entry) => (
                    <div key={entry.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <Badge>{entry.entity_type}</Badge>
                        <p className="text-sm font-medium">{entry.action}</p>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">
                        {entry.actor_name ?? "Unknown user"} · {formatDateTime(entry.created_at)}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">Brand activity appears here once changes are made.</p>
                )}
              </div>
            </Card>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Field({ children, className, label }: { children: ReactNode; className?: string; label: string }) {
  return (
    <div className={className}>
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function MiniCount({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-lg font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-1 text-[0.68rem] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
    </div>
  );
}

function SectionJumpButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      className="inline-flex min-h-10 items-center rounded-full border border-slate-200 bg-white/80 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-primary/30 hover:text-primary"
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function SummaryPill({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-[1.25rem] border border-slate-200/80 bg-white/82 px-4 py-3 shadow-sm">
      <p className="text-[0.68rem] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-xl font-semibold tracking-tight text-slate-950">{value}</p>
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

function splitChannels(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function slugifyStageKey(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "") || "stage";
}
