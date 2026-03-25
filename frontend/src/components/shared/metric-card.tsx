import { Card } from "../ui/card";

type MetricCardProps = {
  label: string;
  value: number;
  hint: string;
};

export function MetricCard({ label, value, hint }: MetricCardProps) {
  return (
    <Card className="border-white/70 bg-white/80 p-5 shadow-lg shadow-slate-900/5">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">{label}</p>
      <p className="mt-4 text-4xl font-semibold tracking-tight">{value}</p>
      <p className="mt-3 text-sm text-muted-foreground">{hint}</p>
    </Card>
  );
}
