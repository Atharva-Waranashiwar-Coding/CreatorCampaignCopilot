import { formatDateTime } from "../../lib/format";
import type { DraftPreviewInput } from "./preview-utils";
import { bodyParagraphs, emailSubject, firstSentence, handleFromName } from "./preview-utils";

type EmailPreviewProps = {
  input: DraftPreviewInput;
};

export function EmailPreview({ input }: EmailPreviewProps) {
  const paragraphs = bodyParagraphs(input.contentBody);

  return (
    <div className="overflow-hidden rounded-[1.7rem] border border-slate-200 bg-white shadow-lg shadow-slate-900/10">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Inbox preview</p>
        <div className="mt-3 rounded-[1.1rem] border border-slate-200 bg-white px-4 py-4">
          <p className="text-sm font-semibold text-foreground">{emailSubject(input)}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {firstSentence(input.contentBody || "Start writing to generate email body preview.")}
          </p>
          <p className="mt-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
            {handleFromName(input.brandName)} · {input.plannedPublishAt ? formatDateTime(input.plannedPublishAt) : "Draft preview"}
          </p>
        </div>
      </div>

      <div className="px-6 py-6">
        <div className="rounded-[1.25rem] border border-slate-200 px-5 py-5">
          <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">To: subscribers</p>
          <h3 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">{emailSubject(input)}</h3>
          <p className="mt-2 text-sm text-muted-foreground">{input.campaignName} · {input.brandName}</p>

          <div className="mt-5 space-y-4 text-sm leading-7 text-foreground">
            {(paragraphs.length ? paragraphs : ["Write body copy to see the email layout populate."]).map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </div>

          <button className="mt-6 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" type="button">
            Read more
          </button>
        </div>
      </div>
    </div>
  );
}
