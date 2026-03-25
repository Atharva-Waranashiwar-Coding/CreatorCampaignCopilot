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

  return (
    <div>
      <PageHeader
        eyebrow="Brands"
        title="Brand workspaces and memberships"
        description="Create the top-level workspace, manage foundational brand metadata, and see the invite-ready membership structure."
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <h2 className="text-xl font-semibold tracking-tight">Create brand</h2>
          <form
            className="mt-5 space-y-4"
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
            <Field label="Description">
              <Textarea
                value={createForm.description}
                onChange={(event) =>
                  setCreateForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </Field>
            <Field label="Guidelines summary">
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

            <MutationFeedback error={createMutation.error} />
            <Button className="w-full" disabled={createMutation.isPending} type="submit">
              {createMutation.isPending ? "Creating..." : "Create brand"}
            </Button>
          </form>
        </Card>

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold tracking-tight">Your brands</h2>
              <Badge tone="muted">{brandsQuery.data?.length ?? 0} total</Badge>
            </div>

            <div className="mt-5 space-y-3">
              {brandsQuery.data?.length ? (
                brandsQuery.data.map((brand) => (
                  <button
                    key={brand.id}
                    className={[
                      "w-full rounded-[1.25rem] border px-4 py-4 text-left transition",
                      selectedBrandId === brand.id
                        ? "border-primary bg-primary/5"
                        : "border-border bg-white/80 hover:bg-white",
                    ].join(" ")}
                    onClick={() => setSelectedBrandId(brand.id)}
                    type="button"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base font-semibold">{brand.name}</h3>
                      <Badge>{brand.current_user_role}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{brand.description ?? "No description yet."}</p>
                    <div className="mt-4 flex flex-wrap gap-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      <span>{brand.membership_count} members</span>
                      <span>{brand.project_count} projects</span>
                      <span>{brand.campaign_count} campaigns</span>
                    </div>
                  </button>
                ))
              ) : (
                <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  Create your first brand to unlock projects, campaigns, and memberships.
                </p>
              )}
            </div>
          </Card>

          {selectedBrand ? (
            <div className="grid gap-6 2xl:grid-cols-[1fr_0.95fr]">
              <div className="space-y-6">
                <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Selected brand</p>
                      <h2 className="mt-2 text-2xl font-semibold tracking-tight">{selectedBrand.name}</h2>
                    </div>
                    <Badge>{selectedBrand.current_user_role}</Badge>
                  </div>

                  <form
                    className="mt-5 space-y-4"
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
                    <Field label="Description">
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
                    <Field label="Guidelines summary">
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

                    <MutationFeedback error={updateMutation.error} />
                    <div className="flex flex-wrap gap-3">
                      <Button disabled={updateMutation.isPending} type="submit" variant="primary">
                        {updateMutation.isPending ? "Saving..." : "Save changes"}
                      </Button>
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
                  </form>
                </Card>

                <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Draft workflow</p>
                      <h2 className="mt-2 text-2xl font-semibold tracking-tight">Custom lifecycle stages</h2>
                    </div>
                    <Badge tone="muted">{workflowStages.length} stages</Badge>
                  </div>

                  <p className="mt-3 text-sm leading-6 text-muted-foreground">
                    Define the stage order, initial entry points, and allowed transitions that drafts can follow inside this brand.
                  </p>

                  <div className="mt-5 space-y-4">
                    {workflowStages.map((stage, index) => (
                      <div key={stage.key} className="rounded-[1.25rem] border border-border bg-white/80 p-4">
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

                        <div className="mt-4 grid gap-4 md:grid-cols-3">
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

                        <Field label="Description">
                          <Textarea
                            className="min-h-[80px]"
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

                        <div className="mt-4">
                          <p className="text-sm font-medium text-foreground">Allowed next stages</p>
                          <div className="mt-3 grid gap-2 md:grid-cols-2">
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

                  <MutationFeedback error={workflowMutation.error} />
                  <div className="mt-5 flex flex-wrap gap-3">
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
                </Card>
              </div>

              <div className="space-y-6">
                <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="text-xl font-semibold tracking-tight">Members</h2>
                    <Badge tone="muted">{membershipsQuery.data?.length ?? 0} listed</Badge>
                  </div>

                  <form
                    className="mt-5 grid gap-3 md:grid-cols-[1fr_180px_auto]"
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
                    <Select
                      value={inviteRole}
                      onChange={(event) => setInviteRole(event.target.value as BrandRole)}
                    >
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

                  <MutationFeedback error={inviteMutation.error} />

                  <div className="mt-5 space-y-3">
                    {membershipsQuery.data?.length ? (
                      membershipsQuery.data.map((membership) => (
                        <div
                          key={membership.id}
                          className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4"
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

                <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
                  <div className="flex items-center justify-between gap-3">
                    <h2 className="text-xl font-semibold tracking-tight">Audit activity</h2>
                    <Badge tone="muted">{auditQuery.data?.length ?? 0} entries</Badge>
                  </div>

                  <div className="mt-5 space-y-3">
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
            </div>
          ) : null}
        </div>
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
