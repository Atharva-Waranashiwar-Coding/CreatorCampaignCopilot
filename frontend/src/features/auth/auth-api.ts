import { apiRequest } from "../../lib/api";
import type { AuthResponse, User } from "../../lib/types";

type AuthPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = AuthPayload & {
  full_name: string;
};

export function login(payload: AuthPayload) {
  return apiRequest<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function register(payload: RegisterPayload) {
  return apiRequest<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser(token: string) {
  return apiRequest<User>("/auth/me", {}, token);
}
