import { Badge } from "../ui/badge";
import type { DraftPreviewInput } from "./preview-utils";
import { bodyLines, handleFromName, initials, previewTitle } from "./preview-utils";

type InstagramCaptionPreviewProps = {
  input: DraftPreviewInput;
};

export function InstagramCaptionPreview({ input }: InstagramCaptionPreviewProps) {
  const lines = bodyLines(input.contentBody);
  const captionLines = lines.length ? lines : ["Write a caption to see the Instagram preview populate."];

  return (
    <div className="overflow-hidden rounded-[1.8rem] border border-zinc-200 bg-white shadow-lg shadow-slate-900/10">
      <div className="aspect-square bg-gradient-to-br from-amber-200 via-rose-200 to-cyan-200 px-5 py-5">
        <div className="flex h-full flex-col justify-between rounded-[1.4rem] border border-white/50 bg-white/20 p-5 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/70 text-sm font-semibold text-foreground">
              {initials(input.brandName)}
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">{handleFromName(input.brandName)}</p>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-700">{input.campaignName}</p>
            </div>
          </div>

          <div>
            <p className="text-2xl font-semibold tracking-tight text-foreground">{previewTitle(input)}</p>
            <p className="mt-3 max-w-xs text-sm leading-6 text-slate-800">
              Caption-first preview with room for hooks, line breaks, and hashtags.
            </p>
          </div>
        </div>
      </div>

      <div className="px-5 py-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{handleFromName(input.brandName)}</span>
          <span>Saved</span>
        </div>

        <div className="mt-4 space-y-3 text-sm leading-6 text-foreground">
          {captionLines.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Badge>{input.platform || "Instagram"}</Badge>
          <Badge tone="muted">{input.contentType || "Caption"}</Badge>
        </div>
      </div>
    </div>
  );
}
