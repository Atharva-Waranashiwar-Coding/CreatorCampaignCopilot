import type { PropsWithChildren } from "react";

import { Sidebar } from "./sidebar";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen px-4 py-6 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-7xl gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Sidebar />
        <main className="rounded-[1.5rem] border border-white/70 bg-white/60 p-6 shadow-xl shadow-slate-900/5 backdrop-blur md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
