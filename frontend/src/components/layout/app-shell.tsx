import type { PropsWithChildren } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { MobileNavigation, Sidebar } from "./sidebar";
import { getNavigationItem } from "./navigation";

type AppShellProps = PropsWithChildren<{
  notificationUnreadCount: number;
  userName: string;
  userEmail: string;
  onLogout: () => void;
}>;

function initialsFromName(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function AppShell({ children, notificationUnreadCount, userName, userEmail, onLogout }: AppShellProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentItem = getNavigationItem(location.pathname);

  return (
    <div className="min-h-screen px-3 py-3 md:px-5 md:py-5">
      <div className="mx-auto flex max-w-[1600px] gap-5">
        <Sidebar
          notificationUnreadCount={notificationUnreadCount}
          userName={userName}
          userEmail={userEmail}
          onLogout={onLogout}
        />

        <div className="min-w-0 flex-1">
          <header className="sticky top-3 z-20 rounded-[1.75rem] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(252,249,244,0.9))] px-4 py-4 shadow-[0_16px_50px_-30px_rgba(15,23,42,0.55)] backdrop-blur md:px-6 md:py-5">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="muted">{currentItem?.sectionLabel ?? "Workspace"}</Badge>
                  {notificationUnreadCount ? <Badge tone="warning">{notificationUnreadCount} unread</Badge> : null}
                </div>
                <p className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">
                  {currentItem?.label ?? "Workspace"}
                </p>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 md:text-base">
                  {currentItem?.hint ?? "Navigate the workspace, track delivery, and keep content moving."}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="hidden rounded-[1.25rem] border border-slate-200 bg-white/80 px-3 py-2 shadow-sm md:flex md:items-center md:gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground">
                    {initialsFromName(userName)}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-950">{userName}</p>
                    <p className="truncate text-xs text-slate-500">{userEmail}</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  onClick={() => {
                    onLogout();
                    navigate("/login");
                  }}
                >
                  Log out
                </Button>
              </div>
            </div>

            <div className="mt-4">
              <MobileNavigation notificationUnreadCount={notificationUnreadCount} />
            </div>
          </header>

          <main className="mt-5 min-w-0 overflow-hidden rounded-[2rem] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(250,246,239,0.88))] p-4 shadow-[0_24px_80px_-40px_rgba(15,23,42,0.6)] backdrop-blur md:p-6 xl:p-8">
            <div className="min-w-0">{children}</div>
          </main>
        </div>
      </div>
    </div>
  );
}
