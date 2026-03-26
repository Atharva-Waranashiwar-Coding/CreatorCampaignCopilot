import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "../../lib/types";

type AuthState = {
  token: string | null;
  user: User | null;
  hydrated: boolean;
  setAuth: (payload: { token: string; user: User }) => void;
  setUser: (user: User) => void;
  clearAuth: () => void;
  markHydrated: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hydrated: false,
      setAuth: ({ token, user }) => set({ token, user }),
      setUser: (user) => set({ user }),
      clearAuth: () => set({ token: null, user: null }),
      markHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "creator-campaign-copilot-auth",
      partialize: (state) => ({ token: state.token, user: state.user }),
      onRehydrateStorage: () => (state) => {
        state?.markHydrated();
      },
    },
  ),
);
