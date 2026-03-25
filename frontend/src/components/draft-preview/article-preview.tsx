import { formatDateTime } from "../../lib/format";
import { Badge } from "../ui/badge";
import type { DraftPreviewInput } from "./preview-utils";
import { bodyParagraphs, previewTitle } from "./preview-utils";

type ArticlePreviewProps = {
  input: DraftPreviewInput;
};

export function ArticlePreview({ input }: ArticlePreviewProps) {
  const paragraphs = bodyParagraphs(input.contentBody);

  return (
    <div className="rounded-[1.7rem] border border-stone-200 bg-stone-50 shadow-lg shadow-stone-900/10">
      <div className="border-b border-stone-200 px-6 py-5">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="muted">{input.contentType || "Article"}</Badge>
          <Badge>{input.platform || "Editorial"}</Badge>
        </div>
        <h3 className="mt-4 text-3xl font-semibold tracking-tight text-foreground">{previewTitle(input)}</h3>
        <p className="mt-3 text-sm text-muted-foreground">
          {input.brandName} · {input.campaignName}
          {input.plannedPublishAt ? ` · ${formatDateTime(input.plannedPublishAt)}` : ""}
        </p>
      </div>

      <div className="px-6 py-6">
        <div className="space-y-5 text-[15px] leading-8 text-foreground">
          {(paragraphs.length ? paragraphs : ["Add long-form copy to preview the article layout."]).map((paragraph, index) => (
            <p key={`${paragraph}-${index}`} className={index === 0 ? "text-lg leading-8 text-slate-700" : ""}>
              {paragraph}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
