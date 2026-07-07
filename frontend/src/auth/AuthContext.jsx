import { createContext, useContext, useEffect, useState } from "react";
import { apiFetch, getToken, setToken, clearToken } from "../api/client.js";

// Holds the logged-in user's {id, role, username} in memory so every
// page/component can read it via useAuth() instead of re-fetching.
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On page load/refresh, if a token is already saved, ask the backend
  // who it belongs to. This is what keeps you logged in after a refresh.
  useEffect(() => {
    async function loadUser() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiFetch("/auth/me");
        setUser(me);
      } catch {
        clearToken();
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, []);

  async function login(username, password) {
    // /auth/login expects OAuth2 form-encoded data, not JSON.
    const body = new URLSearchParams({ username, password });
    const data = await apiFetch("/auth/login", {
      method: "POST",
      body,
      isForm: true,
      auth: false,
    });

    // 2FA-enabled accounts (admin only) don't get a real token yet - just
    // a short-lived pending_token the caller has to redeem via
    // completeTwoFactorLogin() once the user enters their code.
    if (data.requires_2fa) {
      return { requires2fa: true, pendingToken: data.pending_token };
    }

    setToken(data.access_token);
    const me = await apiFetch("/auth/me");
    setUser(me);
    return me;
  }

  async function completeTwoFactorLogin(pendingToken, code) {
    const data = await apiFetch("/auth/2fa/login-verify", {
      method: "POST",
      body: { pending_token: pendingToken, code },
      auth: false,
    });
    setToken(data.access_token);
    const me = await apiFetch("/auth/me");
    setUser(me);
    return me;
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  // Re-fetches /auth/me and updates the shared user object - needed
  // after enabling/disabling 2FA, since that flips user.totp_enabled
  // without a fresh login happening.
  async function refreshUser() {
    const me = await apiFetch("/auth/me");
    setUser(me);
    return me;
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, login, completeTwoFactorLogin, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
