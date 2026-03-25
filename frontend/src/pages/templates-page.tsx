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
import { formatDateTime } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { Brand, ContentTemplate } from "../lib/types";

const templateTypeOptions = ["content_draft", "campaign_brief", "review_note", "launch_copy"];

type TemplateFormState = {
  name: string;
  description: string;
  template_type: string;
  platform: string;
  content_type: string;
  body: string;
};

const emptyTemplateForm: TemplateFormState = {
  name: "",
  description: "",
  template_type: "content_draft",
  platform: "",
  content_type: "",
  body: "",
};

export function TemplatesPage() {
  const token = useAuthStore((state) => state.token);
  const [selectedBrandId, setSelectedBrandId] = useState<number | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [createForm, setCreateForm] = useState<TemplateFormState>(emptyTemplateForm);
  const [editForm, setEditForm] = useState<TemplateFormState>(emptyTemplateForm);

  const brandsQuery = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiRequest<Brand[]>("/brands", {}, token),
  });

  useEffect(() => {
    if (!brandsQuery.data?.length) {
      setSelectedBrandId(null);
      return;
    }

    if (!selectedBrandId || !brandsQuery.data.some((brand) => brand.id === selectedBrandId)) {
      setSelectedBrandId(brandsQuery.data[0].id);
    }
  }, [brandsQuery.data, selectedBrandId]);

  const templatesQuery = useQuery({
    queryKey: ["templates", selectedBrandId, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (selectedBrandId) {
        params.set("brand_id", String(selectedBrandId));
      }
      if (search.trim()) {
        params.set("search", search.trim());
      }
      const suffix = params.toString() ? `?${params.toString()}` : "";
      return apiRequest<ContentTemplate[]>(`/templates${suffix}`, {}, token);
    },
    enabled: Boolean(selectedBrandId),
  });

  const selectedTemplate = useMemo(
    () => templatesQuery.data?.find((item) => item.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templatesQuery.data],
  );

  useEffect(() => {
    if (!templatesQuery.data?.length) {
      setSelectedTemplateId(null);
      setEditForm(emptyTemplateForm);
      return;
    }

    if (!selectedTemplateId || !templatesQuery.data.some((item) => item.id === selectedTemplateId)) {
      setSelectedTemplateId(templatesQuery.data[0].id);
      return;
    }

    if (selectedTemplate) {
      setEditForm({
        name: selectedTemplate.name,
        description: selectedTemplate.description ?? "",
        template_type: selectedTemplate.template_type,
        platform: selectedTemplate.platform ?? "",
        content_type: selectedTemplate.content_type ?? "",
        body: selectedTemplate.body,
      });
    }
  }, [selectedTemplate, selectedTemplateId, templatesQuery.data]);

  const createMutation = useMutation({
    mutationFn: (payload: TemplateFormState) =>
      apiRequest<ContentTemplate>(
        "/templates",
        {
          method: "POST",
          body: JSON.stringify({
            ...payload,
            brand_id: selectedBrandId,
            platform: payload.platform || null,
            content_type: payload.content_type || null,
            description: payload.description || null,
          }),
        },
        token,
      ),
    onSuccess: (template) => {
      invalidateTemplateQueries(template.brand_id);
      setSelectedTemplateId(template.id);
      setCreateForm(emptyTemplateForm);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: TemplateFormState) =>
      apiRequest<ContentTemplate>(
        `/templates/${selectedTemplateId}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            ...payload,
            platform: payload.platform || null,
            content_type: payload.content_type || null,
            description: payload.description || null,
          }),
        },
        token,
      ),
    onSuccess: () => {
      if (selectedBrandId) {
        invalidateTemplateQueries(selectedBrandId);
      }
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () =>
      apiRequest<void>(
        `/templates/${selectedTemplateId}`,
        {
          method: "DELETE",
        },
        token,
      ),
    onSuccess: () => {
      if (selectedBrandId) {
        invalidateTemplateQueries(selectedBrandId);
      }
      setSelectedTemplateId(null);
    },
  });

  return (
    <div>
      <PageHeader
        eyebrow="Templates"
        title="Reusable campaign and draft structures"
        description="Save repeatable copy blocks, review notes, and brief patterns at the brand level so each new campaign starts from a stronger baseline."
        actions={(
          <Select
            className="min-w-[220px]"
            value={selectedBrandId ? String(selectedBrandId) : ""}
            onChange={(event) => setSelectedBrandId(Number(event.target.value))}
          >
            {brandsQuery.data?.map((brand) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </Select>
        )}
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold tracking-tight">Create template</h2>
            {selectedBrandId ? <Badge tone="muted">Brand scoped</Badge> : null}
          </div>
          <form
            className="mt-5 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              createMutation.mutate(createForm);
            }}
          >
            <Field label="Template name">
              <Input
                value={createForm.name}
                onChange={(event) => setCreateForm((current) => ({ ...current, name: event.target.value }))}
              />
            </Field>
            <Field label="Template type">
              <Select
                value={createForm.template_type}
                onChange={(event) =>
                  setCreateForm((current) => ({ ...current, template_type: event.target.value }))
                }
              >
                {templateTypeOptions.map((option) => (
                  <option key={option} value={option}>
                    {option.replace(/_/g, " ")}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Platform">
                <Input
                  placeholder="LinkedIn"
                  value={createForm.platform}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, platform: event.target.value }))
                  }
                />
              </Field>
              <Field label="Content type">
                <Input
                  placeholder="Thought leadership"
                  value={createForm.content_type}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, content_type: event.target.value }))
                  }
                />
              </Field>
            </div>
            <Field label="Description">
              <Textarea
                value={createForm.description}
                onChange={(event) =>
                  setCreateForm((current) => ({ ...current, description: event.target.value }))
                }
              />
            </Field>
            <Field label="Template body">
              <Textarea
                className="min-h-[180px]"
                value={createForm.body}
                onChange={(event) => setCreateForm((current) => ({ ...current, body: event.target.value }))}
              />
            </Field>
            <MutationFeedback error={createMutation.error} />
            <Button className="w-full" disabled={createMutation.isPending || !selectedBrandId} type="submit">
              {createMutation.isPending ? "Saving..." : "Create template"}
            </Button>
          </form>
        </Card>

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-semibold tracking-tight">Template library</h2>
              <Badge tone="muted">{templatesQuery.data?.length ?? 0} templates</Badge>
            </div>

            <div className="mt-5">
              <Input
                placeholder="Search template name, description, or body"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            <div className="mt-5 space-y-3">
              {templatesQuery.data?.length ? (
                templatesQuery.data.map((template) => (
                  <button
                    key={template.id}
                    className={[
                      "w-full rounded-[1.25rem] border px-4 py-4 text-left transition",
                      selectedTemplateId === template.id
                        ? "border-primary bg-primary/5"
                        : "border-border bg-white/80 hover:bg-white",
                    ].join(" ")}
                    onClick={() => setSelectedTemplateId(template.id)}
                    type="button"
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <h3 className="text-base font-semibold">{template.name}</h3>
                      <Badge>{template.template_type.replace(/_/g, " ")}</Badge>
                      {template.platform ? <Badge tone="muted">{template.platform}</Badge> : null}
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {template.description ?? "No description provided."}
                    </p>
                    <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                      Updated {formatDateTime(template.updated_at)}
                    </p>
                  </button>
                ))
              ) : (
                <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  Templates will appear here once the selected brand saves reusable copy or brief structures.
                </p>
              )}
            </div>
          </Card>

          {selectedTemplate ? (
            <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Selected template</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">{selectedTemplate.name}</h2>
                </div>
                <Badge tone="muted">{selectedTemplate.template_type.replace(/_/g, " ")}</Badge>
              </div>

              <form
                className="mt-5 space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  updateMutation.mutate(editForm);
                }}
              >
                <Field label="Template name">
                  <Input
                    value={editForm.name}
                    onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))}
                  />
                </Field>
                <Field label="Template type">
                  <Select
                    value={editForm.template_type}
                    onChange={(event) =>
                      setEditForm((current) => ({ ...current, template_type: event.target.value }))
                    }
                  >
                    {templateTypeOptions.map((option) => (
                      <option key={option} value={option}>
                        {option.replace(/_/g, " ")}
                      </option>
                    ))}
                  </Select>
                </Field>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Platform">
                    <Input
                      value={editForm.platform}
                      onChange={(event) =>
                        setEditForm((current) => ({ ...current, platform: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="Content type">
                    <Input
                      value={editForm.content_type}
                      onChange={(event) =>
                        setEditForm((current) => ({ ...current, content_type: event.target.value }))
                      }
                    />
                  </Field>
                </div>
                <Field label="Description">
                  <Textarea
                    value={editForm.description}
                    onChange={(event) =>
                      setEditForm((current) => ({ ...current, description: event.target.value }))
                    }
                  />
                </Field>
                <Field label="Template body">
                  <Textarea
                    className="min-h-[220px]"
                    value={editForm.body}
                    onChange={(event) => setEditForm((current) => ({ ...current, body: event.target.value }))}
                  />
                </Field>
                <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                  <div>
                    <MutationFeedback error={updateMutation.error ?? deleteMutation.error} />
                    <p className="mt-2 text-sm text-muted-foreground">
                      Created by {selectedTemplate.creator_name ?? "Unknown user"} on {formatDateTime(selectedTemplate.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <Button
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate()}
                      type="button"
                      variant="danger"
                    >
                      {deleteMutation.isPending ? "Deleting..." : "Delete"}
                    </Button>
                    <Button disabled={updateMutation.isPending} type="submit">
                      {updateMutation.isPending ? "Saving..." : "Save changes"}
                    </Button>
                  </div>
                </div>
              </form>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );

  function invalidateTemplateQueries(brandId: number) {
    queryClient.invalidateQueries({ queryKey: ["templates"] });
    queryClient.invalidateQueries({ queryKey: ["brand-billing", brandId] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  }
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function MutationFeedback({ error }: { error: Error | null }) {
  if (!error) {
    return null;
  }

  return (
    <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error instanceof ApiError ? error.message : "Something went wrong. Please try again."}
    </p>
  );
}
