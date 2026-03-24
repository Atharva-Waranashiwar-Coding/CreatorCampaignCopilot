import type { HTMLAttributes } from "react";

import { cn } from "../../lib/cn";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-[1.5rem] border border-border bg-card text-card-foreground", className)}
      {...props}
    />
  );
}
