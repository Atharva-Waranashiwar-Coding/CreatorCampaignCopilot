import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select } from "../ui/select";
import { Textarea } from "../ui/textarea";
import { ApiError } from "../../lib/api";
import { formatDateTime, formatStatusLabel } from "../../lib/format";
import type { Assignment, AssignmentEntityType, Membership } from "../../lib/types";

type AssignmentPanelProps = {
  eyebrow: string;
  title: string;
  description: string;
  emptyMessage: string;
  assignments: Assignment[];
  members: Membership[];
  currentUserId: number | null | undefined;
  assignmentTypeOptions: AssignmentEntityType[];
  defaultAssignmentType: AssignmentEntityType;
  isLoading: boolean;
  isCreating: boolean;
  isCompletingId: number | null;
  error: unknown;
  memberError: unknown;
  onCreate: (payload: {
    assignment_type?: AssignmentEntityType;
    assignee_user_id: number;
    note: string | null;
    due_at: string | null;
  }) => Promise<unknown>;
  onComplete: (assignmentId: number) => void;
};

export function AssignmentPanel({
  eyebrow,
  title,
  description,
  emptyMessage,
  assignments,
  members,
  currentUserId,
  assignmentTypeOptions,
  defaultAssignmentType,
  isLoading,
  isCreating,
  isCompletingId,
  error,
  memberError,
  onCreate,
  onComplete,
}: AssignmentPanelProps) {
  const activeMembers = members.filter((member) => member.status === "active" && member.user_id && member.user);
  const [assignmentType, setAssignmentType] = useState<AssignmentEntityType>(defaultAssignmentType);
  const [assigneeUserId, setAssigneeUserId] = useState("");
  const [note, setNote] = useState("");
  const [dueAt, setDueAt] = useState("");

  useEffect(() => {
    setAssignmentType(defaultAssignmentType);
  }, [defaultAssignmentType]);

  useEffect(() => {
    if (!activeMembers.length) {
      setAssigneeUserId("");
      return;
    }

    setAssigneeUserId((current) => {
      if (current && activeMembers.some((member) => String(member.user_id) === current)) {
        return current;
      }
      return String(activeMembers[0].user_id);
    });
  }, [activeMembers]);

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{eyebrow}</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-3 text-sm text-muted-foreground">{description}</p>
        </div>
        <Badge tone="muted">{assignments.length} records</Badge>
      </div>

      <MutationFeedback error={error} />
      <MemberFeedback error={memberError} />

      {activeMembers.length ? (
        <div className="mt-5 rounded-[1.25rem] border border-border bg-white/80 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            {assignmentTypeOptions.length > 1 ? (
              <Field label="Assignment type">
                <Select
                  value={assignmentType}
                  onChange={(event) => setAssignmentType(event.target.value as AssignmentEntityType)}
                >
                  {assignmentTypeOptions.map((option) => (
                    <option key={option} value={option}>
                      {formatStatusLabel(option)}
                    </option>
                  ))}
                </Select>
              </Field>
            ) : null}
            <Field label="Assignee">
              <Select value={assigneeUserId} onChange={(event) => setAssigneeUserId(event.target.value)}>
                {activeMembers.map((member) => (
                  <option key={member.id} value={member.user_id ?? ""}>
                    {member.user?.full_name ?? member.invite_email}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Due at">
              <Input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} />
            </Field>
          </div>

          <div className="mt-4">
            <Label>Assignment note</Label>
            <Textarea
              className="min-h-[96px]"
              placeholder="Brief the assignee on what needs to move next."
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </div>

          <div className="mt-4 flex justify-end">
            <Button
              disabled={isCreating || !assigneeUserId}
              onClick={async () => {
                await onCreate({
                  assignment_type: assignmentTypeOptions.length > 1 ? assignmentType : undefined,
                  assignee_user_id: Number(assigneeUserId),
                  note: note.trim() || null,
                  due_at: dueAt || null,
                });
                setNote("");
                setDueAt("");
              }}
            >
              {isCreating ? "Assigning..." : "Create assignment"}
            </Button>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading assignments...</p>
      ) : assignments.length ? (
        <div className="mt-6 space-y-3">
          {assignments.map((assignment) => (
            <div key={assignment.id} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-sm font-medium text-foreground">
                    {assignment.assignee_name ?? assignment.assignee_email ?? "Unknown assignee"}
                  </p>
                  <Badge>{formatStatusLabel(assignment.assignment_type)}</Badge>
                  <Badge tone={assignment.status === "completed" ? "success" : assignment.status === "canceled" ? "warning" : "muted"}>
                    {formatStatusLabel(assignment.status)}
                  </Badge>
                  {assignment.assignee_user_id === currentUserId ? <Badge tone="success">You</Badge> : null}
                </div>
                {assignment.status === "open" && assignment.assignee_user_id === currentUserId ? (
                  <Button
                    disabled={isCompletingId === assignment.id}
                    onClick={() => onComplete(assignment.id)}
                    variant="secondary"
                  >
                    {isCompletingId === assignment.id ? "Updating..." : "Mark complete"}
                  </Button>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                Assigned by {assignment.assigned_by_name ?? "Unknown user"} · {formatDateTime(assignment.created_at)}
              </p>
              {assignment.due_at ? (
                <p className="mt-2 text-sm text-muted-foreground">Due {formatDateTime(assignment.due_at)}</p>
              ) : null}
              {assignment.note ? <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground">{assignment.note}</p> : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-6 rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
          {emptyMessage}
        </p>
      )}
    </Card>
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
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error.message}
    </p>
  );
}

function MemberFeedback({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      Assignment creation is unavailable here: {error.message}
    </p>
  );
}
