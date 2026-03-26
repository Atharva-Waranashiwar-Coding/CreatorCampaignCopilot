import { cn } from "../../lib/cn";

export type SectionTabItem = {
  value: string;
  label: string;
  description?: string;
  badge?: number | string;
};

type SectionTabsProps = {
  className?: string;
  items: SectionTabItem[];
  onChange: (value: string) => void;
  value: string;
};

export function SectionTabs({ className, items, onChange, value }: SectionTabsProps) {
  const activeItem = items.find((item) => item.value === value);

  return (
    <div className={cn("rounded-[1.5rem] border border-border bg-white/75 p-2", className)}>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => {
          const isActive = item.value === value;

          return (
            <button
              key={item.value}
              className={cn(
                "inline-flex min-h-11 items-center gap-2 rounded-[1rem] px-4 py-2 text-sm font-semibold transition",
                isActive
                  ? "bg-primary text-primary-foreground shadow-[0_12px_26px_-18px_rgba(15,118,135,0.9)]"
                  : "bg-white text-foreground hover:bg-slate-50",
              )}
              onClick={() => onChange(item.value)}
              type="button"
            >
              <span>{item.label}</span>
              {item.badge !== undefined ? (
                <span
                  className={cn(
                    "inline-flex min-w-7 items-center justify-center rounded-full px-2 py-1 text-[0.68rem] font-bold",
                    isActive ? "bg-white/16 text-primary-foreground" : "bg-muted text-muted-foreground",
                  )}
                >
                  {item.badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {activeItem?.description ? (
        <p className="px-2 pb-1 pt-4 text-sm leading-6 text-muted-foreground">{activeItem.description}</p>
      ) : null}
    </div>
  );
}
