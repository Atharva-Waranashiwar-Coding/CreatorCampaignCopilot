import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

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
import { queryClient } from "../lib/query-client";
import type { Brand, Project, ProjectStatus } from "../lib/types";

type ProjectFormState = {
  brand_id: string;
  name: string;
  description: string;
  status: ProjectStatus;
};

const emptyProjectForm: ProjectFormState = {
  brand_id: "",
  name: "",
  description: "",
  status: "active",
};

const statusOptions: ProjectStatus[] = ["active", "archived"];

export function ProjectsPage() {
  const token = useAuthStore((state) => state.token);
  const [brandFilter, setBrandFilter] = useState("all");
  const [createForm, setCreateForm] = useState<ProjectFormState>(emptyProjectForm);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<ProjectFormState>(emptyProjectForm);

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

  useEffect(() => {
    if (!createForm.brand_id && brandsQuery.data?.length) {
      setCreateForm((current) => ({ ...current, brand_id: String(brandsQuery.data[0].id) }));
    }
  }, [brandsQuery.data, createForm.brand_id]);

  const selectedProject = useMemo(
    () => projectsQuery.data?.find((project) => project.id === selectedProjectId) ?? null,
    [projectsQuery.data, selectedProjectId],
  );

  useEffect(() => {
    if (!projectsQuery.data?.length) {
      setSelectedProjectId(null);
      setEditForm(emptyProjectForm);
      return;
    }

    if (!selectedProjectId || !projectsQuery.data.some((project) => project.id === selectedProjectId)) {
      setSelectedProjectId(projectsQuery.data[0].id);
      return;
    }

    if (selectedProject) {
      setEditForm({
        brand_id: String(selectedProject.brand_id),
        name: selectedProject.name,
        description: selectedProject.description ?? "",
        status: selectedProject.status,
      });
    }
  }, [projectsQuery.data, selectedProject, selectedProjectId]);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<Project>(
        "/projects",
        {
          method: "POST",
          body: JSON.stringify({
            brand_id: Number(createForm.brand_id),
            name: createForm.name,
            description: createForm.description,
            status: createForm.status,
          }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
      setCreateForm((current) => ({ ...emptyProjectForm, brand_id: current.brand_id }));
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      apiRequest<Project>(
        `/projects/${selectedProjectId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            name: editForm.name,
            description: editForm.description,
            status: editForm.status,
          }),
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () =>
      apiRequest<void>(
        `/projects/${selectedProjectId}`,
        {
          method: "DELETE",
        },
        token,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["brands"] });
    },
  });

  return (
    <div>
      <PageHeader
        eyebrow="Projects"
        title="Organize work inside each brand"
        description="Projects provide the intermediate structure between a brand workspace and the campaigns that ship under it."
        actions={
          <Select value={brandFilter} onChange={(event) => setBrandFilter(event.target.value)}>
            <option value="all">All brands</option>
            {brandsQuery.data?.map((brand) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </Select>
        }
      />

      <div className="space-y-6">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Create</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Add a new project</h2>
            </div>
            <Badge tone="muted">{projectsQuery.data?.length ?? 0} visible</Badge>
          </div>

          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              createMutation.mutate();
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Brand">
                <Select
                  value={createForm.brand_id}
                  onChange={(event) => setCreateForm((current) => ({ ...current, brand_id: event.target.value }))}
                >
                  {brandsQuery.data?.map((brand) => (
                    <option key={brand.id} value={brand.id}>
                      {brand.name}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Status">
                <Select
                  value={createForm.status}
                  onChange={(event) =>
                    setCreateForm((current) => ({
                      ...current,
                      status: event.target.value as ProjectStatus,
                    }))
                  }
                >
                  {statusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>

            <Field label="Project name">
              <Input
                value={createForm.name}
                onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
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

            <MutationFeedback error={createMutation.error} />
            <Button
              className="w-full sm:w-auto"
              disabled={createMutation.isPending || !brandsQuery.data?.length}
              type="submit"
            >
              {createMutation.isPending ? "Creating..." : "Create project"}
            </Button>
          </form>
        </Card>

        <div className="grid gap-6 xl:grid-cols-[0.96fr_1.04fr]">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Directory</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Project list</h2>
              </div>
              {selectedProject ? <Badge>{selectedProject.name}</Badge> : null}
            </div>

            <div className="mt-5 space-y-3">
              {projectsQuery.data?.length ? (
                projectsQuery.data.map((project) => (
                  <button
                    key={project.id}
                    className={[
                      "w-full rounded-[1.25rem] border px-4 py-4 text-left transition",
                      selectedProjectId === project.id
                        ? "border-primary bg-primary/5"
                        : "border-border bg-white/80 hover:bg-white",
                    ].join(" ")}
                    onClick={() => setSelectedProjectId(project.id)}
                    type="button"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base font-semibold">{project.name}</h3>
                      <Badge tone={project.status === "active" ? "success" : "muted"}>{project.status}</Badge>
                      <Badge tone="muted">{project.campaign_count} campaigns</Badge>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{project.brand_name}</p>
                    <p className="mt-3 text-sm text-muted-foreground">
                      {project.description ?? "No project description yet."}
                    </p>
                  </button>
                ))
              ) : (
                <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  No projects found for the current filter.
                </p>
              )}
            </div>
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            {selectedProject ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Selected project</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight">{selectedProject.name}</h2>
                    <p className="mt-2 text-sm text-muted-foreground">{selectedProject.brand_name}</p>
                  </div>
                  <Badge tone={selectedProject.status === "active" ? "success" : "muted"}>
                    {selectedProject.status}
                  </Badge>
                </div>

                <form
                  className="mt-5 space-y-4"
                  onSubmit={(event) => {
                    event.preventDefault();
                    updateMutation.mutate();
                  }}
                >
                  <Field label="Project name">
                    <Input
                      value={editForm.name}
                      onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))}
                    />
                  </Field>
                  <Field label="Description">
                    <Textarea
                      value={editForm.description}
                      onChange={(event) =>
                        setEditForm((current) => ({ ...current, description: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="Status">
                    <Select
                      value={editForm.status}
                      onChange={(event) =>
                        setEditForm((current) => ({
                          ...current,
                          status: event.target.value as ProjectStatus,
                        }))
                      }
                    >
                      {statusOptions.map((status) => (
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
                        if (window.confirm(`Delete ${selectedProject.name}?`)) {
                          deleteMutation.mutate();
                        }
                      }}
                      type="button"
                      variant="danger"
                    >
                      {deleteMutation.isPending ? "Deleting..." : "Delete project"}
                    </Button>
                  </div>
                </form>
              </>
            ) : (
              <div className="flex h-full min-h-[280px] items-center justify-center rounded-[1.25rem] border border-dashed border-border bg-white/70 px-6 text-center">
                <p className="max-w-sm text-sm leading-6 text-muted-foreground">
                  Select a project from the directory to edit its details here.
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
