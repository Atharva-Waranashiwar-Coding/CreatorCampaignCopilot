import { AppShell } from "../components/layout/app-shell";
import { Card } from "../components/ui/card";

export default function App() {
  return (
    <AppShell>
      <Card className="max-w-3xl border-white/70 bg-white/75 p-8 shadow-xl shadow-slate-900/5 backdrop-blur">
        <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">
          Phase 1 Foundation
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">
          Creator Campaign Copilot
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
          Frontend and backend scaffolding are in place. Brands, memberships, projects,
          campaigns, and auth land in the next implementation slices.
        </p>
      </Card>
    </AppShell>
  );
}
