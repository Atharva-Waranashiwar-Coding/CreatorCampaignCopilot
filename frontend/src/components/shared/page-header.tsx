import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">{eyebrow}</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}
