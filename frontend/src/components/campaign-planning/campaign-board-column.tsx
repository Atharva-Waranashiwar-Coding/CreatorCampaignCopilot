import type { DragEventHandler, ReactNode } from "react";

import type { DraftWorkflowStage } from "../../lib/types";
import { workflowStageMeta } from "./planning-constants";

type CampaignBoardColumnProps = {
  canDrop?: boolean;
  children: ReactNode;
  count: number;
  isActiveDropTarget?: boolean;
  onDragLeave?: DragEventHandler<HTMLDivElement>;
  onDragOver?: DragEventHandler<HTMLDivElement>;
  onDrop?: DragEventHandler<HTMLDivElement>;
  stage: DraftWorkflowStage;
};

export function CampaignBoardColumn({
  canDrop = false,
  children,
  count,
  isActiveDropTarget = false,
  onDragLeave,
  onDragOver,
  onDrop,
  stage,
}: CampaignBoardColumnProps) {
  const meta = workflowStageMeta(stage);

  return (
    <div
      className={[
        "flex min-h-[24rem] flex-col rounded-[1.6rem] border border-border/80 bg-gradient-to-b p-4",
        meta.accentClass,
        canDrop ? "transition-colors" : "",
        isActiveDropTarget ? "border-primary/40 ring-2 ring-primary/15" : "",
      ].join(" ")}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">{meta.label}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{meta.description}</p>
        </div>
        <div className="rounded-full bg-white/80 px-3 py-1 text-xs font-medium text-foreground">
          {count}
        </div>
      </div>

      <div className="mt-4 flex flex-1 flex-col gap-3">
        {children}
      </div>
    </div>
  );
}
