import type { DragEventHandler } from "react";
import { Link } from "react-router-dom";

import { formatActionLabel, formatDateTime, formatStatusLabel } from "../../lib/format";
import type { ContentDraft } from "../../lib/types";
import { Badge } from "../ui/badge";

type DraftBoardCardProps = {
  className?: string;
  draft: ContentDraft;
  draggable?: boolean;
  isDragging?: boolean;
  onDragEnd?: DragEventHandler<HTMLAnchorElement>;
  onDragStart?: DragEventHandler<HTMLAnchorElement>;
};

export function DraftBoardCard({
  className,
  draft,
  draggable = false,
  isDragging = false,
  onDragEnd,
  onDragStart,
}: DraftBoardCardProps) {
  const excerpt = draft.content_body?.replace(/\s+/g, " ").trim() ?? "";

  return (
    <Link
      className={[
        "block rounded-[1.35rem] border border-border bg-white/90 px-4 py-4 shadow-sm shadow-slate-900/5 transition",
        draggable ? "cursor-grab hover:-translate-y-0.5 hover:bg-white" : "hover:bg-white",
        isDragging ? "opacity-60" : "",
        className ?? "",
      ].join(" ")}
      draggable={draggable}
      onDragEnd={onDragEnd}
      onDragStart={onDragStart}
      to={`/drafts/${draft.id}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-foreground">{draft.title}</h3>
        <Badge>{draft.platform}</Badge>
        <Badge tone={draft.status === "approved" || draft.status === "published" ? "success" : draft.status === "in_review" || draft.status === "rejected" ? "warning" : "muted"}>
          {formatStatusLabel(draft.status)}
        </Badge>
      </div>

      <p className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">{draft.content_type}</p>

      {excerpt ? (
        <p className="mt-3 line-clamp-4 text-sm leading-6 text-muted-foreground">
          {excerpt}
        </p>
      ) : (
        <p className="mt-3 rounded-2xl border border-dashed border-border px-3 py-3 text-sm text-muted-foreground">
          No body copy yet. Open the draft to start writing.
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Badge tone="muted">{draft.review_count} reviews</Badge>
        {draft.planned_publish_at ? <Badge tone="muted">Publishes {formatDateTime(draft.planned_publish_at)}</Badge> : null}
      </div>

      {draft.latest_review_action ? (
        <p className="mt-3 text-xs uppercase tracking-[0.16em] text-muted-foreground">
          Latest review {formatActionLabel(draft.latest_review_action)} · {formatDateTime(draft.latest_reviewed_at)}
        </p>
      ) : (
        <p className="mt-3 text-xs uppercase tracking-[0.16em] text-muted-foreground">
          Updated {formatDateTime(draft.updated_at)}
        </p>
      )}
    </Link>
  );
}
