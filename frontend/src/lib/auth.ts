import { jwtDecode } from "jwt-decode";
import type { LoginResponse } from "@/types/user";

const ACCESS_TOKEN_KEY = "lensestate_access_token";
const REFRESH_TOKEN_KEY = "lensestate_refresh_token";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class AuthApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data: unknown) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.data = data;
  }
}

async function parseError(response: Response, fallback: string): Promise<AuthApiError> {
  try {
    const data = (await response.json()) as Record<string, unknown>;
    const message =
      typeof data?.error === "string"
        ? data.error
        : typeof data?.message === "string"
          ? data.message
          : fallback;
    return new AuthApiError(message, response.status, data);
  } catch {
    return new AuthApiError(fallback, response.status, null);
  }
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(access: string, refresh: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
}

export function logout(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export async function refreshToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    logout();
    return null;
  }

  const data = (await response.json()) as { access: string };
  const currentRefresh = getRefreshToken();
  if (data.access && currentRefresh) {
    setTokens(data.access, currentRefresh);
    return data.access;
  }

  return null;
}

export async function logoutRemote(): Promise<void> {
  const refresh = getRefreshToken();
  const access = getAccessToken();
  if (!refresh || !access) return;

  const response = await fetch(`${API_BASE_URL}/api/auth/logout/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${access}`,
    },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) {
    // Best-effort: local logout will still clear tokens.
    return;
  }
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) throw await parseError(response, "Invalid credentials");

  const data = (await response.json()) as LoginResponse;
  setTokens(data.access, data.refresh);
  return data;
}

export async function register(
  username: string,
  email: string,
  password: string,
  phone: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/register/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password, phone }),
  });

  if (!response.ok) throw await parseError(response, "Registration failed.");
}

export async function loginWithGoogle(accessToken: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/google/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  });

  if (!response.ok) throw await parseError(response, "Google login failed.");

  const data = (await response.json()) as LoginResponse;
  setTokens(data.access, data.refresh);
  return data;
}

export async function requestPasswordReset(email: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/password-reset/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  if (!response.ok) throw await parseError(response, "Failed to request password reset.");
}

export async function confirmPasswordReset(
  uid: string,
  token: string,
  password: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/auth/password-reset/confirm/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ uid, token, password }),
  });

  if (!response.ok) throw await parseError(response, "Failed to reset password.");
}

export function isTokenExpired(token: string): boolean {
  try {
    const payload = jwtDecode<{ exp?: number }>(token);
    if (!payload.exp) return true;
    return payload.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}
