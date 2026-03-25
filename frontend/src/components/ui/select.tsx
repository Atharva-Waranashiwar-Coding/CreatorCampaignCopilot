import type { SelectHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-2xl border border-border bg-white px-4 py-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15",
        className,
      )}
      {...props}
    />
  );
}
