import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../components/shared/page-header";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { useAuthStore } from "../features/auth/auth-store";
import { apiRequest } from "../lib/api";
import { formatActionLabel, formatDateTime, formatStatusLabel } from "../lib/format";
import type { Campaign, ContentDraft, DraftStatus } from "../lib/types";

const statusOptions: DraftStatus[] = [
  "idea",
  "draft",
  "in_review",
  "approved",
  "scheduled",
  "published",
  "rejected",
];

export function DraftsPage() {
  const token = useAuthStore((state) => state.token);
  const [campaignFilter, setCampaignFilter] = useState("all");
  const [platformFilter, setPlatformFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  const campaignsQuery = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => apiRequest<Campaign[]>("/campaigns", {}, token),
  });

  const draftsQuery = useQuery({
    queryKey: ["drafts", campaignFilter, platformFilter, statusFilter, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (campaignFilter !== "all") {
        params.set("campaign_id", campaignFilter);
      }
      if (platformFilter.trim()) {
        params.set("platform", platformFilter.trim());
      }
      if (statusFilter !== "all") {
        params.set("status", statusFilter);
      }
      if (search.trim()) {
        params.set("search", search.trim());
      }

      const suffix = params.toString() ? `?${params.toString()}` : "";
      return apiRequest<ContentDraft[]>(`/drafts${suffix}`, {}, token);
    },
  });

  const uniquePlatforms = useMemo(() => {
    const items = new Set(
      (draftsQuery.data ?? []).map((draft) => draft.platform).filter(Boolean),
    );
    return Array.from(items).sort((a, b) => a.localeCompare(b));
  }, [draftsQuery.data]);

  return (
    <div>
      <PageHeader
        eyebrow="Drafts"
        title="All campaign drafts"
        description="Browse the working copy across campaigns, then narrow the list by campaign, platform, status, or free-text search."
        actions={(
          <Link className="inline-flex items-center rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" to="/reviews">
            Open review queue
          </Link>
        )}
      />

      <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xl font-semibold tracking-tight">Draft index</h2>
          <Badge tone="muted">{draftsQuery.data?.length ?? 0} drafts</Badge>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Select value={campaignFilter} onChange={(event) => setCampaignFilter(event.target.value)}>
            <option value="all">All campaigns</option>
            {campaignsQuery.data?.map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {campaign.name}
              </option>
            ))}
          </Select>
          <Select value={platformFilter} onChange={(event) => setPlatformFilter(event.target.value)}>
            <option value="">All platforms</option>
            {uniquePlatforms.map((platform) => (
              <option key={platform} value={platform}>
                {platform}
              </option>
            ))}
          </Select>
          <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All statuses</option>
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {formatStatusLabel(status)}
              </option>
            ))}
          </Select>
          <Input
            placeholder="Search title, body, or type"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
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
                    {formatStatusLabel(draft.status)}
                  </Badge>
                  <Badge tone="muted">{draft.review_count} reviews</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {draft.brand_name} · {draft.project_name} · {draft.campaign_name}
                </p>
                {draft.latest_review_action ? (
                  <p className="mt-3 text-sm text-muted-foreground">
                    Latest review: {formatActionLabel(draft.latest_review_action)} · {formatDateTime(draft.latest_reviewed_at)}
                  </p>
                ) : null}
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
