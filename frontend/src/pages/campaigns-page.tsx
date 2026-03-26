import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

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
import { formatDate } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { Brand, Campaign, CampaignStatus, Project } from "../lib/types";

type CampaignFormState = {
  project_id: string;
  name: string;
  objective: string;
  audience: string;
  campaign_type: string;
  start_date: string;
  end_date: string;
  status: CampaignStatus;
};

const campaignStatusOptions: CampaignStatus[] = ["planning", "active", "completed", "archived"];
const emptyCampaignForm: CampaignFormState = {
  project_id: "",
  name: "",
  objective: "",
  audience: "",
  campaign_type: "",
  start_date: "",
  end_date: "",
  status: "planning",
};

export function CampaignsPage() {
  const token = useAuthStore((state) => state.token);
  const [brandFilter, setBrandFilter] = useState("all");
  const [projectFilter, setProjectFilter] = useState("all");
  const [createForm, setCreateForm] = useState<CampaignFormState>(emptyCampaignForm);
  const [selectedCampaignId, setSelectedCampaignId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<CampaignFormState>(emptyCampaignForm);

  const brandsQuery = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiRequest<Brand[]>("/brands", {}, token),
  });

  const projectsQuery = useQuery({
    queryKey: ["projects", brandFilter],
    queryFn: () =>
      apiRequest<Project[]>(
        brandFilter === "all" ? "/projects" : `/projects?brand_id=${brandFilter}`,
        {},
        token,
      ),
  });

  const campaignsQuery = useQuery({
    queryKey: ["campaigns", brandFilter, projectFilter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (brandFilter !== "all") {
        params.set("brand_id", brandFilter);
      }
      if (projectFilter !== "all") {
        params.set("project_id", projectFilter);
      }
      const suffix = params.toString() ? `?${params.toString()}` : "";
      return apiRequest<Campaign[]>(`/campaigns${suffix}`, {}, token);
    },
  });

  useEffect(() => {
    if (!projectsQuery.data?.length) {
      setProjectFilter("all");
      setCreateForm(emptyCampaignForm);
      return;
    }

    if (projectFilter !== "all" && !projectsQuery.data.some((project) => String(project.id) === projectFilter)) {
      setProjectFilter("all");
    }

    if (
      !createForm.project_id ||
      !projectsQuery.data.some((project) => String(project.id) === createForm.project_id)
    ) {
      setCreateForm((current) => ({ ...current, project_id: String(projectsQuery.data[0].id) }));
    }
  }, [projectsQuery.data, projectFilter, createForm.project_id]);

  const selectedCampaign = useMemo(
    () => campaignsQuery.data?.find((campaign) => campaign.id === selectedCampaignId) ?? null,
    [campaignsQuery.data, selectedCampaignId],
  );

  useEffect(() => {
    if (!campaignsQuery.data?.length) {
      setSelectedCampaignId(null);
      setEditForm(emptyCampaignForm);
      return;
    }

    if (!selectedCampaignId || !campaignsQuery.data.some((campaign) => campaign.id === selectedCampaignId)) {
      setSelectedCampaignId(campaignsQuery.data[0].id);
      return;
    }

    if (selectedCampaign) {
      setEditForm({
        project_id: String(selectedCampaign.project_id),
        name: selectedCampaign.name,
        objective: selectedCampaign.objective ?? "",
        audience: selectedCampaign.audience ?? "",
        campaign_type: selectedCampaign.campaign_type ?? "",
        start_date: selectedCampaign.start_date ?? "",
        end_date: selectedCampaign.end_date ?? "",
        status: selectedCampaign.status,
      });
    }
  }, [campaignsQuery.data, selectedCampaign, selectedCampaignId]);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<Campaign>(
        "/campaigns",
        {
          method: "POST",
          body: JSON.stringify(normalizeCampaignPayload(createForm)),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCreateForm((current) => ({ ...emptyCampaignForm, project_id: current.project_id }));
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      apiRequest<Campaign>(
        `/campaigns/${selectedCampaignId}`,
        {
          method: "PATCH",
          body: JSON.stringify(normalizeCampaignPayload(editForm)),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () =>
      apiRequest<void>(
        `/campaigns/${selectedCampaignId}`,
        {
          method: "DELETE",
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  return (
    <div>
      <PageHeader
        eyebrow="Campaigns"
        title="Plan concrete initiatives inside projects"
        description="Campaigns hold the operational scope, goals, dates, and status for the work that later phases expand with briefs and drafts."
        actions={
          <div className="flex flex-wrap gap-3">
            <Select value={brandFilter} onChange={(event) => setBrandFilter(event.target.value)}>
              <option value="all">All brands</option>
              {brandsQuery.data?.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name}
                </option>
              ))}
            </Select>
            <Select value={projectFilter} onChange={(event) => setProjectFilter(event.target.value)}>
              <option value="all">All projects</option>
              {projectsQuery.data?.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </Select>
          </div>
        }
      />

      <div className="space-y-6">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Create</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Add a campaign</h2>
            </div>
            <Badge tone="muted">{campaignsQuery.data?.length ?? 0} visible</Badge>
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              createMutation.mutate();
            }}
          >
            <Field label="Project">
              <Select
                value={createForm.project_id}
                onChange={(event) => setCreateForm((current) => ({ ...current, project_id: event.target.value }))}
              >
                {projectsQuery.data?.map((project) => (
                  <option key={project.id} value={project.id}>
                    {project.brand_name} · {project.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Campaign name">
              <Input
                value={createForm.name}
                onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
              />
            </Field>
            <Field label="Objective">
              <Textarea
                value={createForm.objective}
                onChange={(event) =>
                  setCreateForm((current) => ({ ...current, objective: event.target.value }))
                }
              />
            </Field>
            <Field label="Audience">
              <Textarea
                value={createForm.audience}
                onChange={(event) =>
                  setCreateForm((current) => ({ ...current, audience: event.target.value }))
                }
              />
            </Field>
            <div className="grid gap-4 md:grid-cols-3">
              <Field label="Type">
                <Input
                  value={createForm.campaign_type}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, campaign_type: event.target.value }))
                  }
                />
              </Field>
              <Field label="Start date">
                <Input
                  type="date"
                  value={createForm.start_date}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, start_date: event.target.value }))
                  }
                />
              </Field>
              <Field label="End date">
                <Input
                  type="date"
                  value={createForm.end_date}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, end_date: event.target.value }))
                  }
                />
              </Field>
            </div>
            <Field label="Status">
              <Select
                value={createForm.status}
                onChange={(event) =>
                  setCreateForm((current) => ({
                    ...current,
                    status: event.target.value as CampaignStatus,
                  }))
                }
              >
                {campaignStatusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </Select>
            </Field>

            <MutationFeedback error={createMutation.error} />
            <Button
              className="w-full sm:w-auto"
              disabled={createMutation.isPending || !projectsQuery.data?.length}
              type="submit"
            >
              {createMutation.isPending ? "Creating..." : "Create campaign"}
            </Button>
          </form>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[0.98fr_1.02fr]">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Directory</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign list</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Select a campaign to edit the fundamentals beside the list, or jump straight into the full workspace.
                </p>
              </div>
              {selectedCampaign ? <Badge>{selectedCampaign.name}</Badge> : null}
            </div>

            <div className="mt-5 space-y-3">
              {campaignsQuery.data?.length ? (
                campaignsQuery.data.map((campaign) => (
                  <button
                    key={campaign.id}
                    className={[
                      "w-full rounded-[1.25rem] border px-4 py-4 text-left transition",
                      selectedCampaignId === campaign.id
                        ? "border-primary bg-primary/5"
                        : "border-border bg-white/80 hover:bg-white",
                    ].join(" ")}
                    onClick={() => setSelectedCampaignId(campaign.id)}
                    type="button"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-3">
                          <h3 className="text-base font-semibold">{campaign.name}</h3>
                          <Badge tone={campaign.status === "active" ? "success" : "muted"}>{campaign.status}</Badge>
                          <Badge tone="muted">{campaign.draft_count} drafts</Badge>
                          {campaign.brief_id ? <Badge tone="success">brief ready</Badge> : <Badge tone="warning">brief missing</Badge>}
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">
                          {campaign.brand_name} · {campaign.project_name}
                        </p>
                        <p className="mt-3 text-sm text-muted-foreground">
                          {campaign.objective ?? "No objective set yet."}
                        </p>
                        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                          {formatDate(campaign.start_date)} to {formatDate(campaign.end_date)}
                        </p>
                      </div>

                      <Link
                        className="inline-flex min-h-11 items-center rounded-[1rem] border border-primary/10 bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-[0_12px_26px_-18px_rgba(15,118,135,0.9)]"
                        onClick={(event) => event.stopPropagation()}
                        to={`/campaigns/${campaign.id}`}
                      >
                        Open workspace
                      </Link>
                    </div>
                  </button>
                ))
              ) : (
                <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  No campaigns found for the current filters.
                </p>
              )}
            </div>
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            {selectedCampaign ? (
              <>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Selected campaign</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight">{selectedCampaign.name}</h2>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {selectedCampaign.brand_name} · {selectedCampaign.project_name}
                    </p>
                  </div>
                  <Badge tone={selectedCampaign.status === "active" ? "success" : "muted"}>
                    {selectedCampaign.status}
                  </Badge>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <Badge tone="muted">{selectedCampaign.draft_count} drafts</Badge>
                  {selectedCampaign.brief_id ? <Badge tone="success">brief ready</Badge> : <Badge tone="warning">brief missing</Badge>}
                  <Link
                    className="inline-flex items-center rounded-[1rem] border border-primary/10 bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-[0_12px_26px_-18px_rgba(15,118,135,0.9)]"
                    to={`/campaigns/${selectedCampaign.id}`}
                  >
                    Open workspace
                  </Link>
                </div>

                <form
                  className="mt-5 space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    updateMutation.mutate();
                  }}
                >
                  <Field label="Campaign name">
                    <Input
                      value={editForm.name}
                      onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))}
                    />
                  </Field>
                  <Field label="Objective">
                    <Textarea
                      value={editForm.objective}
                      onChange={(event) =>
                        setEditForm((current) => ({ ...current, objective: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="Audience">
                    <Textarea
                      value={editForm.audience}
                      onChange={(event) =>
                        setEditForm((current) => ({ ...current, audience: event.target.value }))
                      }
                    />
                  </Field>
                  <div className="grid gap-4 md:grid-cols-3">
                    <Field label="Type">
                      <Input
                        value={editForm.campaign_type}
                        onChange={(event) =>
                          setEditForm((current) => ({ ...current, campaign_type: event.target.value }))
                        }
                      />
                    </Field>
                    <Field label="Start date">
                      <Input
                        type="date"
                        value={editForm.start_date}
                        onChange={(event) =>
                          setEditForm((current) => ({ ...current, start_date: event.target.value }))
                        }
                      />
                    </Field>
                    <Field label="End date">
                      <Input
                        type="date"
                        value={editForm.end_date}
                        onChange={(event) =>
                          setEditForm((current) => ({ ...current, end_date: event.target.value }))
                        }
                      />
                    </Field>
                  </div>
                  <Field label="Status">
                    <Select
                      value={editForm.status}
                      onChange={(event) =>
                        setEditForm((current) => ({
                          ...current,
                          status: event.target.value as CampaignStatus,
                        }))
                      }
                    >
                      {campaignStatusOptions.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </Select>
                  </Field>

                  <MutationFeedback error={updateMutation.error || deleteMutation.error} />
                  <div className="flex flex-wrap gap-3">
                    <Button disabled={updateMutation.isPending} type="submit">
                      {updateMutation.isPending ? "Saving..." : "Save changes"}
                    </Button>
                    <Button
                      disabled={deleteMutation.isPending}
                      onClick={() => {
                        if (window.confirm(`Delete ${selectedCampaign.name}?`)) {
                          deleteMutation.mutate();
                        }
                      }}
                      type="button"
                      variant="danger"
                    >
                      {deleteMutation.isPending ? "Deleting..." : "Delete campaign"}
                    </Button>
                  </div>
                </form>
              </>
            ) : (
              <div className="flex h-full min-h-[320px] items-center justify-center rounded-[1.25rem] border border-dashed border-border bg-white/70 px-6 text-center">
                <p className="max-w-sm text-sm leading-6 text-muted-foreground">
                  Select a campaign from the directory to edit its core setup here.
                </p>
              </div>
            )}
          </Card>
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

function normalizeCampaignPayload(form: CampaignFormState) {
  return {
    project_id: Number(form.project_id),
    name: form.name,
    objective: form.objective || null,
    audience: form.audience || null,
    campaign_type: form.campaign_type || null,
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    status: form.status,
  };
}
