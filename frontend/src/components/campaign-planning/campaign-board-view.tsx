import { useMemo, useState } from "react";

import type { BrandRole, ContentDraft, DraftWorkflow } from "../../lib/types";
import { CampaignBoardColumn } from "./campaign-board-column";
import { DraftBoardCard } from "./draft-board-card";
import { canMoveDraftToStage, emptyColumnMessage, groupDraftsByStatus, workflowBoardStages } from "./planning-constants";

type CampaignBoardViewProps = {
  blockedReasonsByDraftId?: Record<number, string[]>;
  currentUserRole?: BrandRole;
  drafts: ContentDraft[];
  isMovingDraftId?: number | null;
  onMoveDraft?: (draft: ContentDraft, targetStatus: string) => void;
  workflow: DraftWorkflow;
};

export function CampaignBoardView({
  blockedReasonsByDraftId = {},
  currentUserRole,
  drafts,
  isMovingDraftId = null,
  onMoveDraft,
  workflow,
}: CampaignBoardViewProps) {
  const groupedDrafts = useMemo(() => groupDraftsByStatus(drafts, workflow), [drafts, workflow]);
  const boardStages = useMemo(() => workflowBoardStages(workflow), [workflow]);
  const [draggingDraftId, setDraggingDraftId] = useState<number | null>(null);
  const [activeDropStatus, setActiveDropStatus] = useState<string | null>(null);

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
      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}
      >
        {boardStages.map((stage) => {
          const items = groupedDrafts.get(stage.key) ?? [];
          const canDrop = Boolean(draggingDraft && canMoveDraftToStage(draggingDraft, stage, workflow, currentUserRole));

          return (
            <CampaignBoardColumn
              key={stage.key}
              canDrop={canDrop}
              count={items.length}
              isActiveDropTarget={activeDropStatus === stage.key}
              onDragLeave={() => {
                if (activeDropStatus === stage.key) {
                  setActiveDropStatus(null);
                }
              }}
              onDragOver={(event) => {
                if (!canDrop) {
                  return;
                }
                event.preventDefault();
                event.dataTransfer.dropEffect = "move";
                if (activeDropStatus !== stage.key) {
                  setActiveDropStatus(stage.key);
                }
              }}
              onDrop={(event) => {
                event.preventDefault();
                if (!draggingDraft || !canDrop || !onMoveDraft) {
                  resetDragState();
                  return;
                }
                onMoveDraft(draggingDraft, stage.key);
                resetDragState();
              }}
              stage={stage}
            >
              {items.length ? (
                items.map((draft) => (
                  <DraftBoardCard
                    key={draft.id}
                    blockedLabels={blockedReasonsByDraftId[draft.id] ?? []}
                    draft={draft}
                    draggable={Boolean(onMoveDraft && currentUserRole && isDraftDraggable(draft, workflow, currentUserRole))}
                    isDragging={draggingDraftId === draft.id || isMovingDraftId === draft.id}
                    onDragEnd={() => resetDragState()}
                    onDragStart={(event) => {
                      if (!onMoveDraft || !currentUserRole || !isDraftDraggable(draft, workflow, currentUserRole)) {
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
                  {emptyColumnMessage(stage)}
                </div>
              )}
            </CampaignBoardColumn>
          );
        })}
      </div>
    </div>
  );
}

function isDraftDraggable(draft: ContentDraft, workflow: DraftWorkflow, role: BrandRole) {
  return workflowBoardStages(workflow).some((stage) => canMoveDraftToStage(draft, stage, workflow, role));
}
