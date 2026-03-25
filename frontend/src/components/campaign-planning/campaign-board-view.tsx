import { useMemo, useState } from "react";

import type { BrandRole, ContentDraft, DraftStatus } from "../../lib/types";
import { CampaignBoardColumn } from "./campaign-board-column";
import { DraftBoardCard } from "./draft-board-card";
import { boardColumnMeta, canMoveDraftToStage, groupDraftsByStatus, primaryBoardStatuses } from "./planning-constants";

type CampaignBoardViewProps = {
  currentUserRole?: BrandRole;
  drafts: ContentDraft[];
  isMovingDraftId?: number | null;
  onMoveDraft?: (draft: ContentDraft, targetStatus: DraftStatus) => void;
};

export function CampaignBoardView({
  currentUserRole,
  drafts,
  isMovingDraftId = null,
  onMoveDraft,
}: CampaignBoardViewProps) {
  const groupedDrafts = useMemo(() => groupDraftsByStatus(drafts), [drafts]);
  const [draggingDraftId, setDraggingDraftId] = useState<number | null>(null);
  const [activeDropStatus, setActiveDropStatus] = useState<DraftStatus | null>(null);

  const draggingDraft = useMemo(
    () => drafts.find((draft) => draft.id === draggingDraftId) ?? null,
    [draggingDraftId, drafts],
  );

  function resetDragState() {
    setDraggingDraftId(null);
    setActiveDropStatus(null);
  }

  return (
    <div>
      <div className="grid gap-4 xl:grid-cols-3 2xl:grid-cols-6">
        {primaryBoardStatuses.map((status) => {
          const items = groupedDrafts.get(status) ?? [];
          const canDrop = Boolean(draggingDraft && canMoveDraftToStage(draggingDraft.status, status, currentUserRole));

          return (
            <CampaignBoardColumn
              key={status}
              canDrop={canDrop}
              count={items.length}
              isActiveDropTarget={activeDropStatus === status}
              onDragLeave={() => {
                if (activeDropStatus === status) {
                  setActiveDropStatus(null);
                }
              }}
              onDragOver={(event) => {
                if (!canDrop) {
                  return;
                }
                event.preventDefault();
                event.dataTransfer.dropEffect = "move";
                if (activeDropStatus !== status) {
                  setActiveDropStatus(status);
                }
              }}
              onDrop={(event) => {
                event.preventDefault();
                if (!draggingDraft || !canDrop || !onMoveDraft) {
                  resetDragState();
                  return;
                }
                onMoveDraft(draggingDraft, status);
                resetDragState();
              }}
              status={status}
            >
              {items.length ? (
                items.map((draft) => (
                  <DraftBoardCard
                    key={draft.id}
                    draft={draft}
                    draggable={Boolean(onMoveDraft && currentUserRole && isDraftDraggable(draft.status, currentUserRole))}
                    isDragging={draggingDraftId === draft.id || isMovingDraftId === draft.id}
                    onDragEnd={() => resetDragState()}
                    onDragStart={(event) => {
                      if (!onMoveDraft || !currentUserRole || !isDraftDraggable(draft.status, currentUserRole)) {
                        event.preventDefault();
                        return;
                      }
                      event.dataTransfer.effectAllowed = "move";
                      event.dataTransfer.setData("text/plain", String(draft.id));
                      setDraggingDraftId(draft.id);
                    }}
                  />
                ))
              ) : (
                <div className="rounded-[1.25rem] border border-dashed border-border bg-white/70 px-4 py-6 text-sm text-muted-foreground">
                  {emptyColumnMessage(status)}
                </div>
              )}
            </CampaignBoardColumn>
          );
        })}
      </div>

      {(groupedDrafts.get("rejected") ?? []).length ? (
        <div className="mt-6 rounded-[1.6rem] border border-rose-200 bg-rose-50/80 p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-rose-600">{boardColumnMeta.rejected.label}</p>
              <h3 className="mt-2 text-lg font-semibold tracking-tight text-foreground">Feedback loop</h3>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                Rejected items stay visible outside the main board because they require review context before moving back to in review.
              </p>
            </div>
            <div className="rounded-full bg-white px-3 py-1 text-xs font-medium text-rose-700">
              {(groupedDrafts.get("rejected") ?? []).length} needs changes
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {(groupedDrafts.get("rejected") ?? []).map((draft) => (
              <DraftBoardCard
                key={draft.id}
                draft={draft}
                draggable={Boolean(onMoveDraft && currentUserRole && canMoveDraftToStage("rejected", "in_review", currentUserRole))}
                isDragging={draggingDraftId === draft.id || isMovingDraftId === draft.id}
                onDragEnd={() => resetDragState()}
                onDragStart={(event) => {
                  if (!onMoveDraft || !currentUserRole || !canMoveDraftToStage("rejected", "in_review", currentUserRole)) {
                    event.preventDefault();
                    return;
                  }
                  event.dataTransfer.effectAllowed = "move";
                  event.dataTransfer.setData("text/plain", String(draft.id));
                  setDraggingDraftId(draft.id);
                }}
              />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function emptyColumnMessage(status: DraftStatus) {
  switch (status) {
    case "idea":
      return "New concepts land here before the first working draft exists.";
    case "draft":
      return "Working copy will appear here once ideas become active drafts.";
    case "in_review":
      return "Nothing is waiting on reviewers right now.";
    case "approved":
      return "Approved drafts are ready to move into schedule.";
    case "scheduled":
      return "Scheduled work will stack here before publish.";
    case "published":
      return "Published work becomes the campaign archive.";
    case "rejected":
      return "Rejected drafts appear here while changes are in flight.";
  }
}

function isDraftDraggable(status: DraftStatus, role: BrandRole) {
  return primaryBoardStatuses.some((targetStatus) => canMoveDraftToStage(status, targetStatus, role));
}
