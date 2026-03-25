import { Card } from "../ui/card";

type MetricCardProps = {
  label: string;
  value: number;
  hint: string;
};

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <Card className="border-white/80 bg-white/92 p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-slate-500">{label}</p>
        <span className="mt-1 h-2.5 w-2.5 rounded-full bg-primary/75" />
      </div>
      <div className="mt-6 flex items-end justify-between gap-4">
        <p className="text-4xl font-semibold tracking-tight text-slate-950">{value}</p>
        <p className="max-w-[11rem] text-right text-xs leading-5 text-slate-500">{hint}</p>
      </div>
    </Card>
  );
}
