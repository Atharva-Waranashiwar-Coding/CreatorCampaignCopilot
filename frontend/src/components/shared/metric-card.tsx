import { Card } from "../ui/card";

type MetricCardProps = {
  label: string;
  value: number;
  hint: string;
};

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <Card className="border-white/80 bg-white/92 p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.22em] text-slate-500">{label}</p>
        <span className="h-2.5 w-2.5 rounded-full bg-primary/75" />
      </div>
      <p className="mt-4 text-4xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-3 text-xs leading-5 text-slate-500">{hint}</p>
    </Card>
  );
}
