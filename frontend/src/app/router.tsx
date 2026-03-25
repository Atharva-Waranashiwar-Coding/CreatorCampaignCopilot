import { useEffect } from "react";
import { Navigate, NavLink, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "../components/layout/app-shell";
import { Card } from "../components/ui/card";
import { getCurrentUser } from "../features/auth/auth-api";
import { useAuthStore } from "../features/auth/auth-store";
import { DashboardPage } from "../pages/dashboard-page";
import { DraftDetailPage } from "../pages/draft-detail-page";
import { DraftsPage } from "../pages/drafts-page";
import { BrandsPage } from "../pages/brands-page";
import { CampaignOverviewPage } from "../pages/campaign-overview-page";
import { CampaignsPage } from "../pages/campaigns-page";
import { LoginPage } from "../pages/login-page";
import { ProjectsPage } from "../pages/projects-page";

function ProtectedLayout() {
  const location = useLocation();
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const hydrated = useAuthStore((state) => state.hydrated);

  const meQuery = useQuery({
    queryKey: ["auth", "me", token],
    queryFn: () => getCurrentUser(token!),
    enabled: hydrated && Boolean(token),
    retry: false,
  });

  useEffect(() => {
    if (meQuery.data) {
      setUser(meQuery.data);
    }
  }, [meQuery.data, setUser]);

  useEffect(() => {
    if (meQuery.isError) {
      clearAuth();
    }
  }, [clearAuth, meQuery.isError]);

  if (!hydrated) {
    return <LoadingCard label="Restoring session" />;
  }

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (meQuery.isLoading && !user) {
    return <LoadingCard label="Loading workspace" />;
  }

  return (
    <AppShell
      userName={user?.full_name ?? meQuery.data?.full_name ?? "Campaign operator"}
      userEmail={user?.email ?? meQuery.data?.email ?? ""}
      onLogout={clearAuth}
    >
      <Outlet />
    </AppShell>
  );
}

function AuthRedirect() {
  const token = useAuthStore((state) => state.token);
  const hydrated = useAuthStore((state) => state.hydrated);

  if (!hydrated) {
    return <LoadingCard label="Preparing session" />;
  }

  return token ? <Navigate to="/" replace /> : <LoginPage />;
}

function NotFound() {
  return (
    <Card className="mx-auto mt-12 max-w-xl border-white/70 bg-white/80 p-8 shadow-xl shadow-slate-900/5">
      <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Not Found</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">Route does not exist</h1>
      <p className="mt-3 text-muted-foreground">
        The requested page is outside the current phase scope.
      </p>
      <NavLink className="mt-6 inline-flex text-sm font-medium text-primary" to="/">
        Return to dashboard
      </NavLink>
    </Card>
  );
}

function LoadingCard({ label }: { label: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md border-white/70 bg-white/80 p-8 text-center shadow-xl shadow-slate-900/5">
        <p className="text-sm uppercase tracking-[0.3em] text-muted-foreground">{label}</p>
        <div className="mt-6 h-2 overflow-hidden rounded-full bg-muted">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-primary" />
        </div>
      </Card>
    </div>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<AuthRedirect />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/brands" element={<BrandsPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/campaigns" element={<CampaignsPage />} />
        <Route path="/campaigns/:campaignId" element={<CampaignOverviewPage />} />
        <Route path="/drafts" element={<DraftsPage />} />
        <Route path="/drafts/:draftId" element={<DraftDetailPage />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
