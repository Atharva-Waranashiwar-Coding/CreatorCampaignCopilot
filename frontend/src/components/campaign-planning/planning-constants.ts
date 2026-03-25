import type { BrandRole, ContentDraft, DraftWorkflow, DraftWorkflowStage } from "../../lib/types";

export type PlannerView = "board" | "list" | "calendar";

const workspaceRoles: BrandRole[] = ["owner", "admin", "editor"];
const reviewRoles: BrandRole[] = ["owner", "admin", "reviewer"];

const colorClassMap: Record<string, string> = {
  amber: "from-amber-100 to-white",
  sky: "from-sky-100 to-white",
  emerald: "from-emerald-100 to-white",
  cyan: "from-cyan-100 to-white",
  rose: "from-rose-100 to-white",
  orange: "from-orange-100 to-white",
  blue: "from-blue-100 to-white",
  slate: "from-slate-200 to-white",
};

export function workflowStageMap(workflow: DraftWorkflow) {
  return new Map(workflow.stages.map((stage) => [stage.key, stage]));
}

export function workflowBoardStages(workflow: DraftWorkflow) {
  return workflow.stages;
}

export function workflowStageMeta(stage: DraftWorkflowStage) {
  return {
    accentClass: colorClassMap[stage.color] ?? "from-slate-100 to-white",
    description: stage.description ?? defaultStageDescription(stage),
    label: stage.label,
  };
}

export function groupDraftsByStatus(drafts: ContentDraft[], workflow: DraftWorkflow) {
  const groups = new Map<string, ContentDraft[]>();
  workflow.stages.forEach((stage) => groups.set(stage.key, []));

  drafts.forEach((draft) => {
    groups.set(draft.status, [...(groups.get(draft.status) ?? []), draft]);
  });

  groups.forEach((items, status) => {
    groups.set(
      status,
      items.sort((left, right) => right.updated_at.localeCompare(left.updated_at)),
    );
  });

  return groups;
}

export function canMoveDraftToStage(
  draft: ContentDraft,
  targetStage: DraftWorkflowStage,
  workflow: DraftWorkflow,
  role: BrandRole | undefined,
) {
  if (!role || draft.status === targetStage.key) {
    return false;
  }

  const currentStage = workflowStageMap(workflow).get(draft.status);
  if (!currentStage || !currentStage.allowed_next_stage_keys.includes(targetStage.key)) {
    return false;
  }

  if (targetStage.stage_type === "changes_requested") {
    return false;
  }

  if (targetStage.stage_type === "approved") {
    return reviewRoles.includes(role);
  }

  if (targetStage.stage_type === "review") {
    return workspaceRoles.includes(role);
  }

  if (currentStage.stage_type === "review") {
    return false;
  }

  return workspaceRoles.includes(role);
}

export function emptyColumnMessage(stage: DraftWorkflowStage) {
  switch (stage.stage_type) {
    case "backlog":
      return "Early concepts land here before active drafting begins.";
    case "in_progress":
      return "Working drafts will collect here while copy is in motion.";
    case "review":
      return "Nothing is waiting on reviewer feedback right now.";
    case "approved":
      return "Approved work will appear here before launch prep.";
    case "scheduled":
      return "Scheduled work will stack here before publish.";
    case "published":
      return "Shipped content becomes the campaign archive.";
    case "changes_requested":
      return "Requested changes stay visible here until the next pass.";
  }
}

function defaultStageDescription(stage: DraftWorkflowStage) {
  switch (stage.stage_type) {
    case "backlog":
      return "Loose concepts and early hooks.";
    case "in_progress":
      return "Working copy in active editing.";
    case "review":
      return "Waiting on reviewer feedback.";
    case "approved":
      return "Cleared and ready to schedule.";
    case "scheduled":
      return "Placed on the campaign calendar.";
    case "published":
      return "Live and shipped.";
    case "changes_requested":
      return "Needs changes before the next review pass.";
  }
}
