// Small fetch wrapper shared by every page.
// Centralizing this means the auth header and error handling
// only need to be written once, instead of in every component.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "phd_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// Wraps fetch(): adds the API base URL, adds the Bearer token
// if we have one, and throws a readable error on non-2xx responses
// so callers can just try/catch instead of checking res.ok everywhere.
export async function apiFetch(path, { method = "GET", body, auth = true, isForm = false } = {}) {
  const headers = {};

  if (!isForm) {
    headers["Content-Type"] = "application/json";
  }

  if (auth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // some endpoints may return no body
  }

  if (!res.ok) {
    const message =
      (data && (data.detail?.error || data.detail || data.message)) ||
      `Request failed with status ${res.status}`;
    const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
    error.status = res.status;
    error.data = data;
    throw error;
  }

  return data;
}
