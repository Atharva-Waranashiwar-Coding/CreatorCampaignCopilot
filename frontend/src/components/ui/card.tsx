import type { HTMLAttributes } from "react";

import { cn } from "../../lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "min-w-0 overflow-hidden rounded-[1.6rem] border border-white/80 bg-card/95 text-card-foreground shadow-[0_18px_50px_-36px_rgba(15,23,42,0.7)] backdrop-blur-sm",
        className,
      )}
      {...props}
    />
  );
}
