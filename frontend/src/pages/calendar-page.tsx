import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
import { formatDateTime, formatStatusLabel } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { CalendarItem, Campaign } from "../lib/types";

type CalendarFormState = {
  campaign_id: string;
  title: string;
  item_type: string;
  scheduled_for: string;
  platform: string;
  status: string;
  notes: string;
};

const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const emptyCalendarForm: CalendarFormState = {
  campaign_id: "",
  title: "",
  item_type: "campaign_milestone",
  scheduled_for: "",
  platform: "",
  status: "",
  notes: "",
};

export function CalendarPage() {
  const token = useAuthStore((state) => state.token);
  const [monthCursor, setMonthCursor] = useState(() => startOfMonth(new Date()));
  const [campaignFilter, setCampaignFilter] = useState("all");
  const [platformFilter, setPlatformFilter] = useState("all");
  const [form, setForm] = useState<CalendarFormState>(emptyCalendarForm);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [selectedModalItem, setSelectedModalItem] = useState<CalendarItem | null>(null);

  const gridDays = useMemo(() => buildCalendarGrid(monthCursor), [monthCursor]);
  const rangeStart = gridDays[0];
  const rangeEnd = endOfDay(gridDays[gridDays.length - 1]);
  const monthLabel = new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(monthCursor);

  const campaignsQuery = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => apiRequest<Campaign[]>("/campaigns", {}, token),
  });

  const calendarQuery = useQuery({
    queryKey: ["calendar-items", rangeStart.toISOString(), rangeEnd.toISOString(), campaignFilter],
    queryFn: () => {
      const params = new URLSearchParams({
        start: rangeStart.toISOString(),
        end: rangeEnd.toISOString(),
      });
      if (campaignFilter !== "all") {
        params.set("campaign_id", campaignFilter);
      }
      return apiRequest<CalendarItem[]>(`/calendar-items?${params.toString()}`, {}, token);
    },
  });

  useEffect(() => {
    if (form.campaign_id || !campaignsQuery.data?.length) {
      return;
    }

    setForm((current) => ({
      ...current,
      campaign_id: campaignFilter !== "all" ? campaignFilter : String(campaignsQuery.data[0].id),
    }));
  }, [campaignFilter, campaignsQuery.data, form.campaign_id]);

  useEffect(() => {
    if (!isItemModalOpen) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeItemModal();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isItemModalOpen]);

  const visibleItems = useMemo(() => {
    const items = calendarQuery.data ?? [];
    return items
      .filter((item) => {
      if (platformFilter !== "all" && item.platform !== platformFilter) {
        return false;
      }
      return true;
      })
      .sort((left, right) => left.scheduled_for.localeCompare(right.scheduled_for));
  }, [calendarQuery.data, platformFilter]);

  const itemsByDay = useMemo(() => {
    const grouped = new Map<string, CalendarItem[]>();
    visibleItems.forEach((item) => {
      const key = toDateKey(new Date(item.scheduled_for));
      const dayItems = grouped.get(key) ?? [];
      dayItems.push(item);
      dayItems.sort((left, right) => left.scheduled_for.localeCompare(right.scheduled_for));
      grouped.set(key, dayItems);
    });
    return grouped;
  }, [visibleItems]);

  const platformOptions = useMemo(() => {
    const values = new Set(
      visibleItems
        .map((item) => item.platform)
        .filter((item): item is string => Boolean(item)),
    );
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }, [visibleItems]);

  const saveItemMutation = useMutation({
    mutationFn: () => {
      const path = editingItemId ? `/calendar-items/${editingItemId}` : "/calendar-items";
      const method = editingItemId ? "PATCH" : "POST";
      const body = editingItemId
        ? JSON.stringify({
            title: form.title,
            item_type: form.item_type,
            scheduled_for: form.scheduled_for,
            platform: form.platform || null,
            status: form.status || null,
            notes: form.notes || null,
          })
        : JSON.stringify({
            campaign_id: Number(form.campaign_id),
            title: form.title,
            item_type: form.item_type,
            scheduled_for: form.scheduled_for,
            platform: form.platform || null,
            status: form.status || null,
            notes: form.notes || null,
          });
      return apiRequest<CalendarItem>(path, { method, body }, token);
    },
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", String(item.campaign_id)] });
      setEditingItemId(null);
      setSelectedModalItem(null);
      setIsItemModalOpen(false);
      setForm({
        ...emptyCalendarForm,
        campaign_id: resolveDefaultCampaignId(campaignFilter, campaignsQuery.data, form.campaign_id),
      });
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: (item: CalendarItem) =>
      apiRequest<void>(`/calendar-items/${item.id}`, {
        method: "DELETE",
      }, token),
    onSuccess: (_, item) => {
      queryClient.invalidateQueries({ queryKey: ["calendar-items"] });
      queryClient.invalidateQueries({ queryKey: ["campaign-overview", String(item.campaign_id)] });
      if (editingItemId === item.id) {
        setEditingItemId(null);
        setSelectedModalItem(null);
        setIsItemModalOpen(false);
        setForm({
          ...emptyCalendarForm,
          campaign_id: resolveDefaultCampaignId(campaignFilter, campaignsQuery.data, form.campaign_id),
        });
      }
    },
  });

  const openCreateModal = (day?: Date) => {
    const scheduledFor = new Date(day ?? new Date());
    if (day) {
      scheduledFor.setHours(9, 0, 0, 0);
    }

    setSelectedModalItem(null);
    setEditingItemId(null);
    setForm({
      ...emptyCalendarForm,
      campaign_id: resolveDefaultCampaignId(campaignFilter, campaignsQuery.data, form.campaign_id),
      scheduled_for: toDateTimeLocal(scheduledFor),
    });
    setIsItemModalOpen(true);
  };

  const openItemModal = (item: CalendarItem) => {
    setSelectedModalItem(item);
    if (item.draft_id) {
      setEditingItemId(null);
    } else {
      setEditingItemId(item.id);
      setForm(toCalendarForm(item));
    }
    setIsItemModalOpen(true);
  };

  function closeItemModal() {
    setIsItemModalOpen(false);
    setSelectedModalItem(null);
    setEditingItemId(null);
    setForm({
      ...emptyCalendarForm,
      campaign_id: resolveDefaultCampaignId(campaignFilter, campaignsQuery.data, form.campaign_id),
    });
  }

  if (campaignsQuery.isLoading || calendarQuery.isLoading) {
    return (
      <Card className="border-white/70 bg-white/85 p-8 shadow-xl shadow-slate-900/5">
        <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Loading calendar</p>
      </Card>
    );
  }

  return (
    <div>
      <PageHeader
        eyebrow="Calendar"
        title="Campaign schedule"
        description="Track draft publish dates and campaign milestones in one monthly view, then add manual schedule items for launch operations."
        actions={(
          <div className="flex flex-wrap gap-3">
            <Button disabled={!campaignsQuery.data?.length} onClick={() => openCreateModal()}>
              Add calendar item
            </Button>
            <Link className="inline-flex min-h-11 items-center rounded-[1rem] border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-foreground shadow-sm" to="/campaigns">
              Open campaigns
            </Link>
          </div>
        )}
      />

      <div className="space-y-6">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Monthly view</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">{monthLabel}</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => setMonthCursor((current) => shiftMonth(current, -1))} type="button" variant="secondary">
                Previous
              </Button>
              <Button onClick={() => setMonthCursor(startOfMonth(new Date()))} type="button" variant="ghost">
                Today
              </Button>
              <Button onClick={() => setMonthCursor((current) => shiftMonth(current, 1))} type="button" variant="secondary">
                Next
              </Button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <Select value={campaignFilter} onChange={(event) => setCampaignFilter(event.target.value)}>
              <option value="all">All campaigns</option>
              {campaignsQuery.data?.map((campaign) => (
                <option key={campaign.id} value={campaign.id}>
                  {campaign.name}
                </option>
              ))}
            </Select>
            <Select value={platformFilter} onChange={(event) => setPlatformFilter(event.target.value)}>
              <option value="all">All platforms</option>
              {platformOptions.map((platform) => (
                <option key={platform} value={platform}>
                  {platform}
                </option>
              ))}
            </Select>
            <div className="flex items-center rounded-[1rem] border border-border bg-white/80 px-4 text-sm text-muted-foreground">
              {visibleItems.length} scheduled items
            </div>
          </div>

          <div className="mt-6 grid grid-cols-7 gap-2 text-center text-xs uppercase tracking-[0.2em] text-muted-foreground">
            {weekdayLabels.map((label) => (
              <div key={label} className="rounded-2xl border border-transparent px-2 py-2">
                {label}
              </div>
            ))}
          </div>

          <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-7">
            {gridDays.map((day) => {
              const dayKey = toDateKey(day);
              const dayItems = itemsByDay.get(dayKey) ?? [];
              const isCurrentMonth = day.getMonth() === monthCursor.getMonth();
              const isToday = dayKey === toDateKey(new Date());

              return (
                <div
                  key={dayKey}
                  className={[
                    "min-h-[168px] rounded-[1.4rem] border p-3",
                    isCurrentMonth ? "border-border bg-white/80" : "border-border/70 bg-slate-50/70",
                    isToday ? "ring-2 ring-primary/20" : "",
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-2">
                    <button
                      className={["text-left text-sm font-semibold", isCurrentMonth ? "text-foreground" : "text-muted-foreground"].join(" ")}
                      onClick={() => openCreateModal(day)}
                      type="button"
                    >
                      {day.getDate()}
                    </button>
                    <div className="flex items-center gap-2">
                      {dayItems.length ? <Badge tone="muted">{dayItems.length}</Badge> : null}
                      <button
                        className="inline-flex rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-slate-600 transition hover:border-slate-300"
                        onClick={() => openCreateModal(day)}
                        type="button"
                      >
                        Add
                      </button>
                    </div>
                  </div>

                  <div className="mt-3 space-y-2">
                    {dayItems.slice(0, 3).map((item) => (
                      <button
                        key={item.id}
                        className="block w-full rounded-[1rem] border border-border bg-white px-3 py-2 text-left transition hover:bg-slate-50"
                        onClick={() => openItemModal(item)}
                        type="button"
                      >
                        <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                          {formatTime(item.scheduled_for)}
                        </p>
                        <p className="mt-1 text-sm font-medium text-foreground">{item.title}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Badge tone={item.draft_id ? "success" : "muted"}>{item.item_type}</Badge>
                          {item.platform ? <Badge tone="muted">{item.platform}</Badge> : null}
                        </div>
                      </button>
                    ))}
                    {dayItems.length > 3 ? (
                      <p className="px-1 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
                        +{dayItems.length - 3} more
                      </p>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Agenda</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Upcoming schedule</h2>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Badge tone="muted">{visibleItems.length} items</Badge>
              <Button disabled={!campaignsQuery.data?.length} onClick={() => openCreateModal()} variant="secondary">
                New item
              </Button>
            </div>
          </div>

          <div className="mt-5 space-y-3">
            {visibleItems.length ? (
              visibleItems.map((item) => (
                <div key={item.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="text-base font-semibold">{item.title}</h3>
                        <Badge tone={item.draft_id ? "success" : "muted"}>{item.item_type}</Badge>
                        {item.status ? <Badge tone="muted">{formatStatusLabel(item.status)}</Badge> : null}
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">
                        {item.campaign_name}
                        {item.platform ? ` · ${item.platform}` : ""}
                        {item.draft_title ? ` · ${item.draft_title}` : ""}
                      </p>
                      <p className="mt-3 text-sm text-foreground">{formatDateTime(item.scheduled_for)}</p>
                      {item.notes ? <p className="mt-3 text-sm leading-6 text-muted-foreground">{item.notes}</p> : null}
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {item.draft_id ? <Badge tone="warning">Draft managed</Badge> : null}
                      <Button onClick={() => openItemModal(item)} type="button" variant="secondary">
                        {item.draft_id ? "View details" : "Edit item"}
                      </Button>
                      <Link className="inline-flex min-h-11 items-center rounded-[1rem] border border-transparent px-4 py-2 text-sm font-semibold text-primary transition hover:border-slate-200 hover:bg-white" to={item.draft_id ? `/drafts/${item.draft_id}` : `/campaigns/${item.campaign_id}`}>
                        Open source
                      </Link>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                Scheduled drafts and manual milestones will appear here for the selected month.
              </p>
            )}
          </div>
        </Card>
      </div>

      {isItemModalOpen ? (
        <CalendarModal onClose={closeItemModal}>
          {selectedModalItem?.draft_id ? (
            <div>
              <div className="flex flex-wrap items-center gap-3">
                <Badge tone="success">{selectedModalItem.item_type}</Badge>
                {selectedModalItem.platform ? <Badge tone="muted">{selectedModalItem.platform}</Badge> : null}
                {selectedModalItem.status ? <Badge tone="muted">{formatStatusLabel(selectedModalItem.status)}</Badge> : null}
              </div>
              <h2 className="mt-4 text-2xl font-semibold tracking-tight">{selectedModalItem.title}</h2>
              <p className="mt-3 text-sm text-muted-foreground">
                {selectedModalItem.campaign_name}
                {selectedModalItem.draft_title ? ` · ${selectedModalItem.draft_title}` : ""}
              </p>
              <p className="mt-4 text-sm text-foreground">{formatDateTime(selectedModalItem.scheduled_for)}</p>
              {selectedModalItem.notes ? (
                <p className="mt-4 text-sm leading-6 text-muted-foreground">{selectedModalItem.notes}</p>
              ) : null}
              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  className="inline-flex min-h-11 items-center rounded-[1rem] border border-primary/10 bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-[0_12px_26px_-18px_rgba(15,118,135,0.9)]"
                  to={selectedModalItem.draft_id ? `/drafts/${selectedModalItem.draft_id}` : `/campaigns/${selectedModalItem.campaign_id}`}
                >
                  Open source
                </Link>
                <Button onClick={closeItemModal} type="button" variant="ghost">
                  Close
                </Button>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Manual milestone</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                    {editingItemId ? "Edit calendar item" : "Add calendar item"}
                  </h2>
                </div>
                {editingItemId ? <Badge tone="warning">Editing</Badge> : <Badge tone="muted">Manual</Badge>}
              </div>

              <form
                className="mt-5 space-y-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  saveItemMutation.mutate();
                }}
              >
                <Field label="Campaign">
                  <Select
                    disabled={Boolean(editingItemId)}
                    value={form.campaign_id}
                    onChange={(event) => setForm((current) => ({ ...current, campaign_id: event.target.value }))}
                  >
                    <option value="">Select campaign</option>
                    {campaignsQuery.data?.map((campaign) => (
                      <option key={campaign.id} value={campaign.id}>
                        {campaign.name}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Field label="Title">
                  <Input
                    value={form.title}
                    onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                  />
                </Field>

                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Item type">
                    <Input
                      placeholder="launch, review, shoot"
                      value={form.item_type}
                      onChange={(event) => setForm((current) => ({ ...current, item_type: event.target.value }))}
                    />
                  </Field>
                  <Field label="Platform">
                    <Input
                      placeholder="Instagram, LinkedIn"
                      value={form.platform}
                      onChange={(event) => setForm((current) => ({ ...current, platform: event.target.value }))}
                    />
                  </Field>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Scheduled for">
                    <Input
                      type="datetime-local"
                      value={form.scheduled_for}
                      onChange={(event) => setForm((current) => ({ ...current, scheduled_for: event.target.value }))}
                    />
                  </Field>
                  <Field label="Status">
                    <Input
                      placeholder="scheduled, blocked, complete"
                      value={form.status}
                      onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}
                    />
                  </Field>
                </div>

                <Field label="Notes">
                  <Textarea
                    className="min-h-[120px]"
                    value={form.notes}
                    onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                  />
                </Field>

                <MutationFeedback error={saveItemMutation.error || deleteItemMutation.error} />
                <div className="flex flex-wrap gap-3">
                  <Button disabled={saveItemMutation.isPending || (!editingItemId && !form.campaign_id)} type="submit">
                    {saveItemMutation.isPending ? "Saving..." : editingItemId ? "Update item" : "Add item"}
                  </Button>
                  {editingItemId && selectedModalItem ? (
                    <Button
                      disabled={deleteItemMutation.isPending}
                      onClick={() => {
                        if (window.confirm(`Delete ${selectedModalItem.title}?`)) {
                          deleteItemMutation.mutate(selectedModalItem);
                        }
                      }}
                      type="button"
                      variant="danger"
                    >
                      {deleteItemMutation.isPending ? "Deleting..." : "Delete item"}
                    </Button>
                  ) : null}
                  <Button onClick={closeItemModal} type="button" variant="ghost">
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          )}
        </CalendarModal>
      ) : null}
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

function CalendarModal({
  children,
  onClose,
}: {
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/40 p-4 md:items-center" onClick={onClose} role="presentation">
      <Card
        className="max-h-[85vh] w-full max-w-3xl overflow-y-auto border-white/70 bg-white/95 p-6 shadow-2xl shadow-slate-900/30"
        onClick={(event) => event.stopPropagation()}
      >
        {children}
      </Card>
    </div>
  );
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function shiftMonth(date: Date, offset: number) {
  return new Date(date.getFullYear(), date.getMonth() + offset, 1);
}

function buildCalendarGrid(month: Date) {
  const firstDay = startOfMonth(month);
  const gridStart = new Date(firstDay);
  gridStart.setDate(firstDay.getDate() - firstDay.getDay());

  return Array.from({ length: 42 }, (_, index) => {
    const day = new Date(gridStart);
    day.setDate(gridStart.getDate() + index);
    return day;
  });
}

function endOfDay(date: Date) {
  const copy = new Date(date);
  copy.setHours(23, 59, 59, 999);
  return copy;
}

function toDateKey(date: Date) {
  return [
    String(date.getFullYear()),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function resolveDefaultCampaignId(
  campaignFilter: string,
  campaigns: Campaign[] | undefined,
  currentCampaignId: string,
) {
  if (campaignFilter !== "all") {
    return campaignFilter;
  }
  if (currentCampaignId) {
    return currentCampaignId;
  }
  return campaigns?.[0] ? String(campaigns[0].id) : "";
}

function toDateTimeLocal(date: Date) {
  const copy = new Date(date);
  const timezoneOffsetMinutes = copy.getTimezoneOffset();
  copy.setMinutes(copy.getMinutes() - timezoneOffsetMinutes);
  return copy.toISOString().slice(0, 16);
}

function toCalendarForm(item: CalendarItem): CalendarFormState {
  return {
    campaign_id: String(item.campaign_id),
    title: item.title,
    item_type: item.item_type,
    scheduled_for: item.scheduled_for.slice(0, 16),
    platform: item.platform ?? "",
    status: item.status ?? "",
    notes: item.notes ?? "",
  };
}
