import { useAuthStore } from "../features/auth/auth-store";

export function useAuth() {
  return useAuthStore((state) => ({
    token: state.token,
    user: state.user,
    hydrated: state.hydrated,
    setAuth: state.setAuth,
    clearAuth: state.clearAuth,
  }));
}
