import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Button } from "../components/ui/button";
import { login, register } from "../features/auth/auth-api";
import { useAuthStore } from "../features/auth/auth-store";
import { ApiError } from "../lib/api";

type Mode = "login" | "register";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((state) => state.setAuth);
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

  const [mode, setMode] = useState<Mode>("register");
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
  });

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "register") {
        return register(form);
      }

      return login({ email: form.email, password: form.password });
    },
    onSuccess: (response) => {
      setAuth({ token: response.access_token, user: response.user });
      navigate(from, { replace: true });
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(255,249,240,0.9))] p-8 shadow-2xl shadow-slate-900/5">
          <p className="text-xs uppercase tracking-[0.35em] text-muted-foreground">Phase 1 Access</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">Creator Campaign Copilot</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            Stand up a brand workspace, create projects, launch campaigns, and keep core operations visible.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              "Email/password JWT auth scaffold",
              "Brand, project, and campaign CRUD",
              "Membership and audit foundations",
            ].map((item) => (
              <div key={item} className="rounded-[1.25rem] border border-border bg-white/80 p-4 text-sm text-muted-foreground">
                {item}
              </div>
            ))}
          </div>
        </Card>

        <Card className="border-white/70 bg-white/88 p-8 shadow-2xl shadow-slate-900/5 backdrop-blur">
          <div className="flex gap-2 rounded-full bg-muted p-1">
            <button
              className={[
                "flex-1 rounded-full px-4 py-2 text-sm font-medium transition",
                mode === "register" ? "bg-white text-foreground shadow" : "text-muted-foreground",
              ].join(" ")}
              onClick={() => setMode("register")}
              type="button"
            >
              Create account
            </button>
            <button
              className={[
                "flex-1 rounded-full px-4 py-2 text-sm font-medium transition",
                mode === "login" ? "bg-white text-foreground shadow" : "text-muted-foreground",
              ].join(" ")}
              onClick={() => setMode("login")}
              type="button"
            >
              Sign in
            </button>
          </div>

          <form
            className="mt-8 space-y-5"
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            {mode === "register" ? (
              <div>
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  placeholder="Avery Morgan"
                  value={form.full_name}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, full_name: event.target.value }))
                  }
                />
              </div>
            ) : null}

            <div>
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                placeholder="team@brand.com"
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              />
            </div>

            <div>
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                placeholder="At least 8 characters"
                type="password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({ ...current, password: event.target.value }))
                }
              />
            </div>

            {mutation.error ? (
              <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {mutation.error instanceof ApiError ? mutation.error.message : "Authentication failed."}
              </p>
            ) : null}

            <Button className="w-full" disabled={mutation.isPending} type="submit">
              {mutation.isPending
                ? "Working..."
                : mode === "register"
                  ? "Create workspace account"
                  : "Sign in"}
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
