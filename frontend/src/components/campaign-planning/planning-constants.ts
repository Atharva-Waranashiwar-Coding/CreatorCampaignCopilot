import type { BrandRole, ContentDraft, DraftStatus } from "../../lib/types";

export type PlannerView = "board" | "list" | "calendar";

export const primaryBoardStatuses: DraftStatus[] = [
  "idea",
  "draft",
  "in_review",
  "approved",
  "scheduled",
  "published",
];

export const secondaryBoardStatuses: DraftStatus[] = ["rejected"];

export const boardColumnMeta: Record<DraftStatus, { accentClass: string; description: string; label: string }> = {
  idea: {
    accentClass: "from-amber-100 to-white",
    description: "Loose concepts and early hooks.",
    label: "Idea",
  },
  draft: {
    accentClass: "from-sky-100 to-white",
    description: "Working copy in active editing.",
    label: "Draft",
  },
  in_review: {
    accentClass: "from-amber-50 to-white",
    description: "Waiting on review feedback.",
    label: "In Review",
  },
  approved: {
    accentClass: "from-emerald-100 to-white",
    description: "Cleared and ready to schedule.",
    label: "Approved",
  },
  scheduled: {
    accentClass: "from-cyan-100 to-white",
    description: "Placed on the campaign calendar.",
    label: "Scheduled",
  },
  published: {
    accentClass: "from-slate-200 to-white",
    description: "Live and shipped.",
    label: "Published",
  },
  rejected: {
    accentClass: "from-rose-100 to-white",
    description: "Needs changes before the next review pass.",
    label: "Needs Changes",
  },
};

const workspaceRoles: BrandRole[] = ["owner", "admin", "editor"];
const reviewRoles: BrandRole[] = ["owner", "admin", "reviewer"];

export function groupDraftsByStatus(drafts: ContentDraft[]) {
  const groups = new Map<DraftStatus, ContentDraft[]>();

  [...primaryBoardStatuses, ...secondaryBoardStatuses].forEach((status) => {
    groups.set(status, []);
  });

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
  currentStatus: DraftStatus,
  targetStatus: DraftStatus,
  role: BrandRole | undefined,
) {
  if (!role || currentStatus === targetStatus || targetStatus === "rejected") {
    return false;
  }

  if (workspaceRoles.includes(role)) {
    if (currentStatus === "idea" && (targetStatus === "draft" || targetStatus === "in_review")) {
      return true;
    }
    if (currentStatus === "draft" && (targetStatus === "idea" || targetStatus === "in_review")) {
      return true;
    }
    if (currentStatus === "rejected" && targetStatus === "in_review") {
      return true;
    }
    if (currentStatus === "approved" && (targetStatus === "scheduled" || targetStatus === "published")) {
      return true;
    }
    if (currentStatus === "scheduled" && targetStatus === "published") {
      return true;
    }
  }

  if (reviewRoles.includes(role) && currentStatus === "in_review" && targetStatus === "approved") {
    return true;
  }

  return false;
}
