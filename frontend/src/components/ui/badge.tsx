import type { HTMLAttributes } from "react";

import { cn } from "../../lib/cn";

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: "default" | "success" | "muted" | "warning";
};

const tones: Record<NonNullable<BadgeProps["tone"]>, string> = {
  default: "border-primary/20 bg-primary text-primary-foreground shadow-primary/20",
  success: "border-emerald-200 bg-emerald-600 text-white shadow-emerald-600/20",
  muted: "border-slate-300 bg-white text-slate-700 shadow-slate-300/30",
  warning: "border-amber-300 bg-amber-400 text-amber-950 shadow-amber-400/25",
};

export function Badge({ className, tone = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center whitespace-nowrap rounded-full border px-3 py-1 text-[0.72rem] font-semibold leading-none shadow-sm",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
