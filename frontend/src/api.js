import { API_BASE } from "./config";

export const TOKEN_KEY = "azmarine_token";
export const USER_KEY = "azmarine_user";

// Migrate legacy keys so existing sessions don't break
if (typeof window !== "undefined") {
  for (const [oldK, newK] of [["nexusaz_token", TOKEN_KEY], ["nexusaz_user", USER_KEY]]) {
    const v = localStorage.getItem(oldK);
    if (v && !localStorage.getItem(newK)) {
      localStorage.setItem(newK, v);
      localStorage.removeItem(oldK);
    }
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Thin fetch wrapper that auto-attaches the bearer token, parses JSON,
 * and throws on non-2xx with a helpful error.
 */
export default async function apiFetch(path, options = {}) {
  const token = getToken();
  const isFormData = options.body instanceof FormData;
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    clearAuth();
    if (!path.startsWith("/auth/login")) {
      window.location.assign("/login");
    }
  }

  let data = null;
  const text = await res.text();
  if (text) {
    try { data = JSON.parse(text); } catch { data = text; }
  }
  if (!res.ok) {
    const detail = (data && data.detail) || res.statusText || "Request failed";
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}
