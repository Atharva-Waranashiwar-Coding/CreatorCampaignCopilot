const navItems = ["Dashboard", "Brands", "Projects", "Campaigns"];

export function Sidebar() {
  return (
    <aside className="rounded-[1.75rem] border border-white/70 bg-[linear-gradient(160deg,rgba(12,86,102,0.96),rgba(16,42,58,0.96))] p-6 text-white shadow-2xl shadow-slate-900/10">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-white/60">Workspace</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight">
          Creator Campaign Copilot
        </h2>
        <p className="mt-3 text-sm leading-6 text-white/70">
          Structured campaign operations for multi-brand teams.
        </p>
      </div>

      <nav className="mt-10 space-y-2">
        {navItems.map((item) => (
          <div
            key={item}
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white/85"
          >
            {item}
          </div>
        ))}
      </nav>
    </aside>
  );
}
