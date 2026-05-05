import { getAccessToken, logout, refreshToken } from "@/lib/auth";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type ApiPaginatedResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

type RequestOptions = RequestInit & {
  skipAuth?: boolean;
  retryOnUnauthorized?: boolean;
};

async function parseError(response: Response): Promise<Error> {
  try {
    const data = (await response.json()) as Record<string, unknown>;
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : typeof data?.message === "string"
          ? data.message
          : typeof data?.error === "string"
            ? data.error
            : "Request failed.";
    return new Error(message);
  } catch {
    return new Error("Request failed.");
  }
}

export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { skipAuth = false, retryOnUnauthorized = true, headers, ...init } = options;

  const requestHeaders = new Headers(headers);
  if (!requestHeaders.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    requestHeaders.set("Content-Type", "application/json");
  }

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) {
      requestHeaders.set("Authorization", `Bearer ${token}`);
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...init,
    headers: requestHeaders,
  });

  if (response.status === 401 && !skipAuth && retryOnUnauthorized) {
    const newAccessToken = await refreshToken();
    if (newAccessToken) {
      return apiRequest<T>(endpoint, {
        ...options,
        retryOnUnauthorized: false,
      });
    }
    logout();
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function buildListingsQuery(
  params: Record<string, string | number | boolean | null | undefined>,
): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") return;
    query.append(key, String(value));
  });
  const queryString = query.toString();
  return queryString ? `?${queryString}` : "";
}

export function get<T>(endpoint: string, options: RequestOptions = {}) {
  return apiRequest<T>(endpoint, { ...options, method: "GET" });
}

export function post<T>(endpoint: string, body?: unknown, options: RequestOptions = {}) {
  return apiRequest<T>(endpoint, {
    ...options,
    method: "POST",
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function put<T>(endpoint: string, body?: unknown, options: RequestOptions = {}) {
  return apiRequest<T>(endpoint, {
    ...options,
    method: "PUT",
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function patch<T>(endpoint: string, body?: unknown, options: RequestOptions = {}) {
  return apiRequest<T>(endpoint, {
    ...options,
    method: "PATCH",
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function del<T>(endpoint: string, options: RequestOptions = {}) {
  return apiRequest<T>(endpoint, { ...options, method: "DELETE" });
}
