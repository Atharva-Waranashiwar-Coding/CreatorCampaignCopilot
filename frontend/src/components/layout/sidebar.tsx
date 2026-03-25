import { NavLink, useNavigate } from "react-router-dom";

import { Button } from "../ui/button";

const navItems = [
  { label: "Dashboard", to: "/" },
  { label: "Brands", to: "/brands" },
  { label: "Projects", to: "/projects" },
  { label: "Campaigns", to: "/campaigns" },
  { label: "Calendar", to: "/calendar" },
  { label: "Drafts", to: "/drafts" },
  { label: "Review Queue", to: "/reviews" },
];

type SidebarProps = {
  userName: string;
  userEmail: string;
  onLogout: () => void;
};

export function Sidebar({ userName, userEmail, onLogout }: SidebarProps) {
  const navigate = useNavigate();

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
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                "block rounded-2xl border px-4 py-3 text-sm font-medium transition",
                isActive
                  ? "border-white/25 bg-white/15 text-white"
                  : "border-white/10 bg-white/5 text-white/85 hover:bg-white/10",
              ].join(" ")
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-10 rounded-2xl border border-white/10 bg-white/5 p-4">
        <p className="text-xs uppercase tracking-[0.25em] text-white/55">Signed in</p>
        <p className="mt-3 text-sm font-medium">{userName}</p>
        <p className="mt-1 text-sm text-white/65">{userEmail}</p>
        <Button
          className="mt-5 w-full bg-white text-slate-900 hover:bg-white/90"
          onClick={() => {
            onLogout();
            navigate("/login");
          }}
        >
          Log out
        </Button>
      </div>
    </aside>
  );
}
