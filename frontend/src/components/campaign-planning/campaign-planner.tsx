import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { formatDateTime } from "../../lib/format";
import type { BrandRole, CampaignPlanningSummary, CalendarItem, ContentDraft } from "../../lib/types";
import { Badge } from "../ui/badge";
import { Card } from "../ui/card";
import { CampaignBoardView } from "./campaign-board-view";
import { CampaignCalendarAgenda } from "./campaign-calendar-agenda";
import { DraftBoardCard } from "./draft-board-card";
import type { PlannerView } from "./planning-constants";

const plannerViews: Array<{ description: string; id: PlannerView; label: string }> = [
  {
    description: "Group work by workflow stage.",
    id: "board",
    label: "Board",
  },
  {
    description: "Scan every draft in one stream.",
    id: "list",
    label: "List",
  },
  {
    description: "Track scheduled milestones and publish dates.",
    id: "calendar",
    label: "Calendar",
  },
];

type CampaignPlannerProps = {
  currentUserRole?: BrandRole;
  drafts: ContentDraft[];
  isMovingDraftId?: number | null;
  onMoveDraft?: (draft: ContentDraft, targetStatus: ContentDraft["status"]) => void;
  planningSummary: CampaignPlanningSummary;
  schedule: CalendarItem[];
};

export function CampaignPlanner({
  currentUserRole,
  drafts,
  isMovingDraftId = null,
  onMoveDraft,
  planningSummary,
  schedule,
}: CampaignPlannerProps) {
  const [view, setView] = useState<PlannerView>("board");

  const summaryCards = useMemo(
    () => [
      {
        label: "In Progress",
        value: planningSummary.idea_count + planningSummary.draft_count + planningSummary.rejected_count,
        hint: "Ideas, active drafts, and revision loops.",
      },
      {
        label: "In Review",
        value: planningSummary.in_review_count,
        hint: "Waiting on reviewer feedback.",
      },
      {
        label: "Scheduled",
        value: planningSummary.scheduled_count,
        hint: "Ready on the campaign calendar.",
      },
      {
        label: "Published",
        value: planningSummary.published_count,
        hint: planningSummary.next_planned_publish_at
          ? `Next publish ${formatDateTime(planningSummary.next_planned_publish_at)}`
          : "No publish date scheduled yet.",
      },
    ],
    [planningSummary],
  );

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Planning workspace</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Campaign planner</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
            Switch between board, list, and calendar views without leaving the campaign workspace. Board moves follow the existing editorial workflow and draft review rules.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge tone="muted">{planningSummary.total_drafts} drafts</Badge>
          <Link className="text-sm font-medium text-primary" to="/drafts">
            Open all drafts
          </Link>
        </div>
      </div>

      <div className="mt-5 grid gap-3 lg:grid-cols-4">
        {summaryCards.map((item) => (
          <div key={item.label} className="rounded-[1.25rem] border border-border bg-white/80 px-4 py-4">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{item.label}</p>
            <p className="mt-3 text-3xl font-semibold tracking-tight">{item.value}</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{item.hint}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <div className="inline-flex rounded-full bg-muted/70 p-1">
          {plannerViews.map((plannerView) => (
            <button
              key={plannerView.id}
              className={[
                "rounded-full px-4 py-2 text-sm font-medium transition",
                view === plannerView.id ? "bg-white text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
              ].join(" ")}
              onClick={() => setView(plannerView.id)}
              type="button"
            >
              {plannerView.label}
            </button>
          ))}
        </div>

        <p className="text-sm text-muted-foreground">
          {plannerViews.find((plannerView) => plannerView.id === view)?.description}
        </p>
      </div>

      <div className="mt-6">
        {view === "board" ? (
          <CampaignBoardView
            currentUserRole={currentUserRole}
            drafts={drafts}
            isMovingDraftId={isMovingDraftId}
            onMoveDraft={onMoveDraft}
          />
        ) : null}

        {view === "list" ? (
          drafts.length ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {drafts.map((draft) => (
                <DraftBoardCard key={draft.id} className="h-full" draft={draft} />
              ))}
            </div>
          ) : (
            <div className="rounded-[1.35rem] border border-dashed border-border bg-white/75 px-6 py-10 text-center">
              <p className="text-sm font-medium text-foreground">No drafts in this campaign yet</p>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Use the draft composer above to create the first working copy, then return here to organize the editorial flow.
              </p>
            </div>
          )
        ) : null}

        {view === "calendar" ? <CampaignCalendarAgenda schedule={schedule} /> : null}
      </div>
    </Card>
  );
}
