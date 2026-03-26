import { NavLink, useNavigate } from "react-router-dom";

import { cn } from "../../lib/cn";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { navigationItems, navigationSections } from "./navigation";

type SidebarProps = {
  notificationUnreadCount: number;
  userName: string;
  userEmail: string;
  onLogout: () => void;
};

function initialsFromName(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function NotificationPill({ count }: { count: number }) {
  if (!count) {
    return null;
  }

  return (
    <span className="inline-flex min-w-7 items-center justify-center rounded-full bg-amber-400 px-2 py-1 text-[0.68rem] font-bold text-slate-950 shadow-sm">
      {count}
    </span>
  );
}

function NavigationLinks({ notificationUnreadCount }: { notificationUnreadCount: number }) {
  return (
    <div className="space-y-6">
      {navigationSections.map((section) => (
        <div key={section.label}>
          <p className="px-1 text-[0.68rem] font-semibold uppercase tracking-[0.26em] text-white/45">
            {section.label}
          </p>
          <div className="mt-3 space-y-2">
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "group block rounded-[1.25rem] border px-4 py-3 transition",
                    isActive
                      ? "border-white/18 bg-white text-slate-950 shadow-lg shadow-slate-950/8"
                      : "border-white/10 bg-white/[0.04] text-white/82 hover:border-white/18 hover:bg-white/[0.08]",
                  )
                }
              >
                {({ isActive }) => (
                  <span className="flex items-start justify-between gap-3">
                    <span className="min-w-0">
                      <span className={cn("block text-sm font-semibold", isActive ? "text-slate-950" : "text-white")}>
                        {item.label}
                      </span>
                      <span className={cn("mt-1 block text-xs leading-5", isActive ? "text-slate-600" : "text-white/58")}>
                        {item.hint}
                      </span>
                    </span>
                    {item.to === "/notifications" ? <NotificationPill count={notificationUnreadCount} /> : null}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function Sidebar({ notificationUnreadCount, userName, userEmail, onLogout }: SidebarProps) {
  const navigate = useNavigate();

  return (
    <aside className="hidden min-h-[calc(100vh-2rem)] min-w-0 w-full flex-col rounded-[2rem] border border-slate-900/10 bg-[linear-gradient(180deg,rgba(14,52,68,0.98),rgba(21,35,48,0.98))] p-5 text-white shadow-[0_28px_80px_-42px_rgba(15,23,42,0.95)] lg:flex lg:sticky lg:top-4">
      <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.05] px-4 py-4">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.32em] text-white/52">Creator Campaign Copilot</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-white">Content ops workspace</h2>
        <p className="mt-2 text-sm leading-6 text-white/62">
          Faster planning, cleaner reviews, and clearer delivery across brands.
        </p>
      </div>

      <div className="mt-6 flex-1 overflow-y-auto pr-1">
        <NavigationLinks notificationUnreadCount={notificationUnreadCount} />
      </div>

      <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.06] p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/14 text-sm font-bold text-white">
            {initialsFromName(userName)}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{userName}</p>
            <p className="truncate text-xs text-white/58">{userEmail}</p>
          </div>
        </div>
        <Button
          className="mt-4 w-full"
          variant="secondary"
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

export function MobileNavigation({ notificationUnreadCount }: { notificationUnreadCount: number }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1 lg:hidden">
      {navigationItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          className={({ isActive }) =>
            cn(
              "shrink-0 rounded-full border px-3 py-2 text-sm font-medium transition",
              isActive
                ? "border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/20"
                : "border-slate-200 bg-white/85 text-slate-700 hover:border-slate-300 hover:bg-white",
            )
          }
        >
          <span className="flex items-center gap-2">
            <span>{item.label}</span>
            {item.to === "/notifications" ? <NotificationPill count={notificationUnreadCount} /> : null}
          </span>
        </NavLink>
      ))}
    </div>
  );
}
