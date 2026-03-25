import { formatDateTime } from "../../lib/format";
import { Badge } from "../ui/badge";
import type { DraftPreviewInput } from "./preview-utils";
import { bodyParagraphs, firstSentence, handleFromName, initials, previewTitle } from "./preview-utils";

type LinkedInPreviewProps = {
  input: DraftPreviewInput;
};

export function LinkedInPreview({ input }: LinkedInPreviewProps) {
  const paragraphs = bodyParagraphs(input.contentBody);

  return (
    <div className="rounded-[1.6rem] border border-slate-200 bg-white shadow-lg shadow-slate-900/10">
      <div className="border-b border-slate-200 px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
            {initials(input.brandName)}
          </div>
          <div>
            <p className="font-semibold text-foreground">{input.brandName}</p>
            <p className="text-sm text-muted-foreground">
              {handleFromName(input.brandName)} · {input.plannedPublishAt ? formatDateTime(input.plannedPublishAt) : "Draft preview"}
            </p>
          </div>
        </div>
      </div>

      <div className="px-5 py-5">
        <p className="text-xl font-semibold tracking-tight text-foreground">{previewTitle(input)}</p>
        <div className="mt-4 space-y-4 text-sm leading-7 text-foreground">
          {(paragraphs.length ? paragraphs : [firstSentence(input.contentBody || "Start writing to populate the post preview.")]).map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <Badge tone="muted">{input.campaignName}</Badge>
          <Badge tone={input.status === "approved" || input.status === "published" ? "success" : "warning"}>
            {input.status.replace(/_/g, " ")}
          </Badge>
        </div>
      </div>

      <div className="flex items-center justify-between border-t border-slate-200 px-5 py-4 text-sm text-muted-foreground">
        <span>143 reactions</span>
        <span>24 comments</span>
        <span>12 reposts</span>
      </div>
    </div>
  );
}
