import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { useAuthStore } from "../../features/auth/auth-store";
import { ApiError, apiRequest } from "../../lib/api";
import { formatDateTime } from "../../lib/format";
import type { RetrieveCampaignAssetsResponse } from "../../lib/types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Input } from "../ui/input";

type CampaignHelperPanelProps = {
  campaignId: number;
};

export function CampaignHelperPanel({ campaignId }: CampaignHelperPanelProps) {
  const token = useAuthStore((state) => state.token);
  const [search, setSearch] = useState("");
  const [assetType, setAssetType] = useState("");

  const assetLookupMutation = useMutation({
    mutationFn: () =>
      apiRequest<RetrieveCampaignAssetsResponse>(
        "/tools/helpers/retrieve-campaign-assets",
        {
          method: "POST",
          body: JSON.stringify({
            campaign_id: campaignId,
            search: search || null,
            asset_type: assetType || null,
          }),
        },
        token,
      ),
  });

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Campaign helper</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Asset retrieval helper</h2>
        </div>
        <Badge tone="muted">Campaign-level tool</Badge>
      </div>

      <p className="mt-4 text-sm leading-6 text-muted-foreground">
        Run the asset retrieval helper with optional search and asset-type filters when the existing library needs a faster targeted pass.
      </p>

      <div className="mt-5 grid gap-4 md:grid-cols-[1fr_0.7fr_auto]">
        <Input
          placeholder="Search notes, names, or mime type"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <Input
          placeholder="Image, deck, video"
          value={assetType}
          onChange={(event) => setAssetType(event.target.value)}
        />
        <Button disabled={assetLookupMutation.isPending} onClick={() => assetLookupMutation.mutate()}>
          {assetLookupMutation.isPending ? "Searching..." : "Run helper"}
        </Button>
      </div>

      <MutationError error={assetLookupMutation.error} />

      {assetLookupMutation.data ? (
        <div className="mt-6 space-y-3">
          <p className="text-sm text-muted-foreground">
            Returned {assetLookupMutation.data.returned} assets from {assetLookupMutation.data.campaign_name}.
          </p>
          {assetLookupMutation.data.assets.length ? (
            assetLookupMutation.data.assets.map((asset) => (
              <div key={asset.id} className="rounded-[1.2rem] border border-border bg-white/80 p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge>{asset.name}</Badge>
                  <Badge tone="muted">{asset.asset_type}</Badge>
                  {asset.mime_type ? <Badge tone="muted">{asset.mime_type}</Badge> : null}
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{asset.notes ?? "No asset notes provided."}</p>
                <p className="mt-2 text-sm text-muted-foreground">Updated {formatDateTime(asset.updated_at)}</p>
                <a
                  className="mt-4 inline-flex text-sm font-medium text-primary"
                  href={asset.file_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Open asset
                </a>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">
              No assets matched the current helper filters. Clear the filters or broaden the search text.
            </p>
          )}
        </div>
      ) : null}
    </Card>
  );
}

function MutationError({ error }: { error: unknown }) {
  if (!(error instanceof ApiError)) {
    return null;
  }

  return (
    <p className="mt-5 rounded-[1.2rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
      {error.message}
    </p>
  );
}
