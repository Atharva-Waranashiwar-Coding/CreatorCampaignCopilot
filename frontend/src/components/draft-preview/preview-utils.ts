import type { DraftStatus } from "../../lib/types";

export type PreviewMode = "auto" | "linkedin" | "instagram" | "email" | "article";
export type ResolvedPreviewKind = Exclude<PreviewMode, "auto"> | "generic";

export type DraftPreviewInput = {
  brandName: string;
  campaignName: string;
  contentBody: string;
  contentType: string;
  plannedPublishAt: string;
  platform: string;
  status: DraftStatus;
  title: string;
};

export function resolvePreviewKind(input: DraftPreviewInput, mode: PreviewMode): ResolvedPreviewKind {
  if (mode !== "auto") {
    return mode;
  }

  const platform = input.platform.toLowerCase();
  const contentType = input.contentType.toLowerCase();

  if (platform.includes("linkedin")) {
    return "linkedin";
  }
  if (platform.includes("instagram") || contentType.includes("caption")) {
    return "instagram";
  }
  if (platform.includes("email") || contentType.includes("email") || contentType.includes("newsletter")) {
    return "email";
  }
  if (platform.includes("blog") || contentType.includes("blog") || contentType.includes("article")) {
    return "article";
  }

  return "generic";
}

export function previewLabel(kind: ResolvedPreviewKind) {
  switch (kind) {
    case "linkedin":
      return "LinkedIn";
    case "instagram":
      return "Instagram";
    case "email":
      return "Email";
    case "article":
      return "Article";
    case "generic":
      return "Generic";
  }
}

export function bodyParagraphs(value: string) {
  return value
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

export function bodyLines(value: string) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function initials(value: string) {
  const tokens = value
    .split(/\s+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (!tokens.length) {
    return "CC";
  }

  return tokens.map((token) => token[0]?.toUpperCase() ?? "").join("");
}

export function handleFromName(value: string) {
  const compact = value.toLowerCase().replace(/[^a-z0-9]+/g, "");
  return compact ? `@${compact}` : "@creatorcampaign";
}

export function previewTitle(input: DraftPreviewInput) {
  if (input.title.trim()) {
    return input.title.trim();
  }

  const firstParagraph = bodyParagraphs(input.contentBody)[0];
  return firstParagraph ? truncate(firstParagraph, 72) : "Untitled draft";
}

export function emailSubject(input: DraftPreviewInput) {
  return input.title.trim() || previewTitle(input);
}

export function firstSentence(value: string) {
  const match = value.trim().match(/(.+?[.!?])(?:\s|$)/);
  return match?.[1] ?? truncate(value.trim(), 120);
}

export function truncate(value: string, length: number) {
  if (value.length <= length) {
    return value;
  }
  return `${value.slice(0, length - 1).trimEnd()}...`;
}
