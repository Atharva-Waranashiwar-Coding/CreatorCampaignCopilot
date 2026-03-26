import { useMemo, useState } from "react";

import { formatStatusLabel } from "../../lib/format";
import { Badge } from "../ui/badge";
import { Card } from "../ui/card";
import { ArticlePreview } from "./article-preview";
import { EmailPreview } from "./email-preview";
import { InstagramCaptionPreview } from "./instagram-caption-preview";
import { LinkedInPreview } from "./linkedin-preview";
import type { DraftPreviewInput, PreviewMode } from "./preview-utils";
import { previewLabel, previewStatusTone, previewTitle, resolvePreviewKind } from "./preview-utils";

const previewModes: Array<{ description: string; mode: PreviewMode; title: string }> = [
  { description: "Detect from platform and content type.", mode: "auto", title: "Auto" },
  { description: "Professional post framing and engagement chrome.", mode: "linkedin", title: "LinkedIn" },
  { description: "Caption-first mobile composition.", mode: "instagram", title: "Instagram" },
  { description: "Inbox and newsletter layout.", mode: "email", title: "Email" },
  { description: "Long-form editorial presentation.", mode: "article", title: "Article" },
];

type PlatformPreviewProps = {
  input: DraftPreviewInput;
};

export function PlatformPreview({ input }: PlatformPreviewProps) {
  const [mode, setMode] = useState<PreviewMode>("auto");
  const resolvedKind = useMemo(() => resolvePreviewKind(input, mode), [input, mode]);

  return (
    <Card className="border-white/70 bg-white/85 p-6 shadow-xl shadow-slate-900/5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">Preview mode</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">{previewLabel(resolvedKind)} preview</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Rendering from the current draft fields so the preview stays live while title, platform, content type, and body copy change.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{input.platform || "No platform"}</Badge>
          <Badge tone="muted">{input.contentType || "No content type"}</Badge>
          <Badge tone={previewStatusTone(input.statusType)}>
            {formatStatusLabel(input.status, input.statusLabel)}
          </Badge>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {previewModes.map((previewMode) => (
          <button
            key={previewMode.mode}
            className={[
              "rounded-full px-4 py-2 text-sm font-medium transition",
              mode === previewMode.mode ? "bg-primary text-primary-foreground" : "bg-muted text-foreground hover:bg-muted/80",
            ].join(" ")}
            onClick={() => setMode(previewMode.mode)}
            type="button"
          >
            {previewMode.title}
          </button>
        ))}
      </div>

      <p className="mt-4 text-sm text-muted-foreground">
        {previewModes.find((previewMode) => previewMode.mode === mode)?.description}
      </p>

      <div className="mt-6">
        {resolvedKind === "linkedin" ? <LinkedInPreview input={input} /> : null}
        {resolvedKind === "instagram" ? <InstagramCaptionPreview input={input} /> : null}
        {resolvedKind === "email" ? <EmailPreview input={input} /> : null}
        {resolvedKind === "article" ? <ArticlePreview input={input} /> : null}
        {resolvedKind === "generic" ? (
          <div className="rounded-[1.6rem] border border-dashed border-border bg-white px-6 py-10 text-center">
            <p className="text-sm font-medium text-foreground">{previewTitle(input)}</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The current platform and content type do not map to a specialized preview yet. Switch modes above to inspect one of the supported layouts.
            </p>
          </div>
        ) : null}
      </div>
    </Card>
  );
}
