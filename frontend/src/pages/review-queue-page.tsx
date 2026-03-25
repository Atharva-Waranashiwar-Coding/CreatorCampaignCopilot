import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { useAuthStore } from "../features/auth/auth-store";
import { apiRequest } from "../lib/api";
import { formatDateTime, formatStatusLabel } from "../lib/format";
import type { ContentDraft } from "../lib/types";

export function ReviewQueuePage() {
  const token = useAuthStore((state) => state.token);

  const queueQuery = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => apiRequest<ContentDraft[]>("/drafts/review-queue", {}, token),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Review Queue"
        title="Drafts waiting for review"
        description="Focus the approval lane on items currently in review, with the latest feedback state surfaced on each draft."
      />

      <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Approval lane</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">Pending decisions</h2>
          </div>
          <Badge tone="warning">{queueQuery.data?.length ?? 0} pending</Badge>
        </div>

        <div className="mt-5 space-y-3">
          {queueQuery.data?.length ? (
            queueQuery.data.map((draft) => (
              <Link
                key={draft.id}
                className="block rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 transition hover:bg-white"
                to={`/drafts/${draft.id}`}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-base font-semibold">{draft.title}</h3>
                  <Badge>{draft.platform}</Badge>
                  <Badge tone="warning">{formatStatusLabel(draft.status)}</Badge>
                  <Badge tone="muted">v{draft.current_version_number}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {draft.brand_name} · {draft.project_name} · {draft.campaign_name}
                </p>
                <div className="mt-3 flex flex-wrap gap-4 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  <span>{draft.review_count} review events</span>
                  <span>Updated {formatDateTime(draft.updated_at)}</span>
                </div>
              </Link>
            ))
          ) : (
            <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
              The review queue is clear right now.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
