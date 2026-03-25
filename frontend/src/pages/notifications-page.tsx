import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError, apiRequest } from "../lib/api";
import { formatDateTime, formatStatusLabel } from "../lib/format";
import { queryClient } from "../lib/query-client";
import type { Assignment, Notification, NotificationSummary } from "../lib/types";

export function NotificationsPage() {
  const token = useAuthStore((state) => state.token);
  const [unreadOnly, setUnreadOnly] = useState(false);

  const summaryQuery = useQuery({
    queryKey: ["notifications", "summary"],
    queryFn: () => apiRequest<NotificationSummary>("/notifications/summary", {}, token),
  });

  const notificationsQuery = useQuery({
    queryKey: ["notifications", unreadOnly],
    queryFn: () =>
      apiRequest<Notification[]>(
        `/notifications?limit=40${unreadOnly ? "&unread_only=true" : ""}`,
        {},
        token,
      ),
  });

  const assignmentsQuery = useQuery({
    queryKey: ["assignments", "mine"],
    queryFn: () => apiRequest<Assignment[]>("/assignments/mine", {}, token),
  });

  const markReadMutation = useMutation({
    mutationFn: (notificationId: number) =>
      apiRequest<Notification>(`/notifications/${notificationId}/read`, { method: "POST" }, token),
    onSuccess: () => invalidateInboxQueries(),
  });

  const markAllMutation = useMutation({
    mutationFn: () => apiRequest<{ updated_count: number }>("/notifications/read-all", { method: "POST" }, token),
    onSuccess: () => invalidateInboxQueries(),
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
      queryClient.invalidateQueries({ queryKey: ["assignments", "mine"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const summary = summaryQuery.data;
  const notifications = notificationsQuery.data ?? [];
  const assignments = assignmentsQuery.data ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Notifications"
        title="Collaboration inbox"
        description="Track mentions, review handoffs, assignment changes, and due-soon reminders without leaving the product."
        actions={(
          <>
            <Badge tone={summary?.unread_count ? "warning" : "muted"}>
              {summary?.unread_count ?? 0} unread
            </Badge>
            <Badge tone={assignments.length ? "success" : "muted"}>
              {assignments.length} open assignments
            </Badge>
          </>
        )}
      />

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Inbox</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Recent notifications</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => setUnreadOnly((current) => !current)} variant="secondary">
                {unreadOnly ? "Show all" : "Unread only"}
              </Button>
              <Button
                disabled={markAllMutation.isPending || !summary?.unread_count}
                onClick={() => markAllMutation.mutate()}
                variant="ghost"
              >
                {markAllMutation.isPending ? "Updating..." : "Mark all read"}
              </Button>
            </div>
          </div>

          <MutationFeedback error={notificationsQuery.error ?? markReadMutation.error ?? markAllMutation.error} />

          {notificationsQuery.isLoading ? (
            <p className="mt-6 text-sm text-muted-foreground">Loading notifications...</p>
          ) : notifications.length ? (
            <div className="mt-6 space-y-3">
              {notifications.map((notification) => {
                const href = notificationHref(notification);
                const isUnread = !notification.read_at;

                return (
                  <div key={notification.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <Badge>{formatStatusLabel(notification.notification_type)}</Badge>
                        <Badge tone={isUnread ? "warning" : "muted"}>{isUnread ? "Unread" : "Read"}</Badge>
                      </div>
                      {isUnread ? (
                        <Button
                          disabled={markReadMutation.isPending}
                          onClick={() => markReadMutation.mutate(notification.id)}
                          variant="ghost"
                        >
                          Mark read
                        </Button>
                      ) : null}
                    </div>
                    <h3 className="mt-3 text-base font-semibold">{notification.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-foreground">{notification.body}</p>
                    <p className="mt-3 text-sm text-muted-foreground">
                      {notification.actor_name ?? "System"} · {formatDateTime(notification.created_at)}
                    </p>
                    {href ? (
                      <Link className="mt-4 inline-flex text-sm font-medium text-primary" to={href}>
                        Open linked item
                      </Link>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="mt-6 rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
              Notifications will appear here when collaboration events start flowing through comments, reviews, and assignments.
            </p>
          )}
        </Card>

        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Unread snapshot</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">Need attention now</h2>
              </div>
              <Badge tone={summary?.recent_unread.length ? "warning" : "muted"}>
                {summary?.recent_unread.length ?? 0} recent
              </Badge>
            </div>

            {summaryQuery.isLoading ? (
              <p className="mt-6 text-sm text-muted-foreground">Loading unread snapshot...</p>
            ) : summary?.recent_unread.length ? (
              <div className="mt-6 space-y-3">
                {summary.recent_unread.map((notification) => (
                  <Link
                    key={notification.id}
                    className="block rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 transition hover:bg-white"
                    to={notificationHref(notification) ?? "/notifications"}
                  >
                    <div className="flex flex-wrap items-center gap-3">
                      <Badge>{formatStatusLabel(notification.notification_type)}</Badge>
                      <p className="text-sm font-medium text-foreground">{notification.title}</p>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{formatDateTime(notification.created_at)}</p>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="mt-6 text-sm text-muted-foreground">
                No unread notifications right now.
              </p>
            )}
          </Card>

          <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Assignments</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">My open work</h2>
              </div>
              <Badge tone={assignments.length ? "success" : "muted"}>{assignments.length} open</Badge>
            </div>

            <MutationFeedback error={assignmentsQuery.error ?? completeAssignmentMutation.error} />

            {assignmentsQuery.isLoading ? (
              <p className="mt-6 text-sm text-muted-foreground">Loading assignments...</p>
            ) : assignments.length ? (
              <div className="mt-6 space-y-3">
                {assignments.map((assignment) => (
                  <div key={assignment.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <Badge>{formatStatusLabel(assignment.assignment_type)}</Badge>
                        {assignment.due_at ? <Badge tone="warning">Due {formatDateTime(assignment.due_at)}</Badge> : null}
                      </div>
                      <Button
                        disabled={completeAssignmentMutation.isPending}
                        onClick={() => completeAssignmentMutation.mutate(assignment.id)}
                        variant="secondary"
                      >
                        {completeAssignmentMutation.isPending ? "Updating..." : "Mark complete"}
                      </Button>
                    </div>
                    <p className="mt-3 text-sm font-medium text-foreground">
                      Assigned by {assignment.assigned_by_name ?? "Unknown user"}
                    </p>
                    {assignment.note ? <p className="mt-2 text-sm leading-6 text-muted-foreground">{assignment.note}</p> : null}
                    <Link className="mt-4 inline-flex text-sm font-medium text-primary" to={assignmentHref(assignment)}>
                      Open assigned item
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-6 text-sm text-muted-foreground">
                No open assignments at the moment.
              </p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function notificationHref(notification: Notification) {
  const draftId = numberFromMetadata(notification.metadata, "draft_id");
  const campaignId = numberFromMetadata(notification.metadata, "campaign_id");

  if (notification.entity_type === "content_draft" || notification.entity_type === "draft" || notification.entity_type === "review_task") {
    const targetDraftId = draftId ?? notification.entity_id;
    return targetDraftId ? `/drafts/${targetDraftId}` : null;
  }

  if (notification.entity_type === "campaign") {
    const targetCampaignId = campaignId ?? notification.entity_id;
    return targetCampaignId ? `/campaigns/${targetCampaignId}` : null;
  }

  return null;
}

function assignmentHref(assignment: Assignment) {
  if (assignment.assignment_type === "campaign") {
    return `/campaigns/${assignment.entity_id}`;
  }
  return `/drafts/${assignment.entity_id}`;
}

function numberFromMetadata(metadata: Record<string, unknown>, key: string) {
  const value = metadata[key];
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string" && value) {
    return Number(value);
  }
  return null;
}

function invalidateInboxQueries() {
  queryClient.invalidateQueries({ queryKey: ["notifications"] });
  queryClient.invalidateQueries({ queryKey: ["assignments", "mine"] });
}

function MutationFeedback({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error.message}
    </p>
  );
}
