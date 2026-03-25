import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-8 flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
      <div className="min-w-0">
        <p className="inline-flex rounded-full border border-slate-200 bg-white/85 px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.26em] text-slate-500 shadow-sm">
          {eyebrow}
        </p>
        <h1 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight tracking-tight text-slate-950 md:text-[2.65rem]">
          {title}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 md:text-base">
          {description}
        </p>
      </div>
      {actions ? <div className="flex w-full flex-wrap gap-3 xl:w-auto xl:justify-end">{actions}</div> : null}
    </div>
  );
}
