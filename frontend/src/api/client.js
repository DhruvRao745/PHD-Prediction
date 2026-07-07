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

// For binary responses (PDF downloads) - apiFetch above always calls
// res.json(), which would break on a real file. Fetches the file with
// the same auth header, then triggers a normal browser "Save As" via a
// throwaway <a> tag instead of navigating there directly (navigating
// would just show the PDF in-tab with no filename control, and would
// drop the Authorization header entirely on a plain link click).
export async function downloadFile(path, filename) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { headers });

  if (!res.ok) {
    let message = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      message = data.detail?.error || data.detail || data.message || message;
    } catch {
      // response wasn't JSON (e.g. a real error page) - keep the default message
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
