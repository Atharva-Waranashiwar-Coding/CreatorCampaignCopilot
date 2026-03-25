import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { useAuthStore } from "../features/auth/auth-store";
import { apiRequest } from "../lib/api";
import { formatDateTime } from "../lib/format";
import type { ContentDraft } from "../lib/types";

export function DraftsPage() {
  const token = useAuthStore((state) => state.token);

  const draftsQuery = useQuery({
    queryKey: ["drafts"],
    queryFn: () => apiRequest<ContentDraft[]>("/drafts", {}, token),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Drafts"
        title="All campaign drafts"
        description="Browse the working copy across campaigns and jump into each draft detail page for editing."
      />

      <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-semibold tracking-tight">Draft index</h2>
          <Badge tone="muted">{draftsQuery.data?.length ?? 0} drafts</Badge>
        </div>

        <div className="mt-5 space-y-3">
          {draftsQuery.data?.length ? (
            draftsQuery.data.map((draft) => (
              <Link
                key={draft.id}
                className="block rounded-[1.25rem] border border-border bg-white/80 px-4 py-4 transition hover:bg-white"
                to={`/drafts/${draft.id}`}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-base font-semibold">{draft.title}</h3>
                  <Badge>{draft.platform}</Badge>
                  <Badge tone={draft.status === "in_review" ? "warning" : draft.status === "approved" ? "success" : "muted"}>
                    {draft.status.replace(/_/g, " ")}
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {draft.brand_name} · {draft.project_name} · {draft.campaign_name}
                </p>
                <p className="mt-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
                  Updated {formatDateTime(draft.updated_at)}
                </p>
              </Link>
            ))
          ) : (
            <p className="rounded-[1.25rem] border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
              Drafts will appear here once they are created from a campaign workspace.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
