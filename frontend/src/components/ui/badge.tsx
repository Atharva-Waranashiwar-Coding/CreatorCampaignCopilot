import type { HTMLAttributes } from "react";

import { cn } from "../../lib/cn";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: "default" | "success" | "muted" | "warning";
};

const tones: Record<NonNullable<BadgeProps["tone"]>, string> = {
  default: "bg-primary/10 text-primary",
  success: "bg-emerald-100 text-emerald-700",
  muted: "bg-slate-200 text-slate-700",
  warning: "bg-amber-100 text-amber-700",
};

export function Badge({ className, tone = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
