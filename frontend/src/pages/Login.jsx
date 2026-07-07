import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { getDashboardPath } from "../utils/roles.js";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, completeTwoFactorLogin } = useAuth();
  const navigate = useNavigate();

  // Only set once /auth/login comes back saying this account has 2FA
  // enabled (admin-only) - switches the form below to the code prompt.
  const [pendingToken, setPendingToken] = useState(null);
  const [code, setCode] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await login(username, password);
      if (result.requires2fa) {
        setPendingToken(result.pendingToken);
      } else {
        navigate(getDashboardPath(result.role));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCodeSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const me = await completeTwoFactorLogin(pendingToken, code);
      navigate(getDashboardPath(me.role));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (pendingToken) {
    return (
      <div className="page">
        <h2>Two-factor authentication</h2>
        <p className="hint">
          Enter the 6-digit code from your authenticator app, or one of
          your backup codes if you don't have access to it.
        </p>
        <form onSubmit={handleCodeSubmit} className="form">
          <label>
            Code
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoFocus
              required
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "Verifying..." : "Verify"}
          </button>
        </form>
        <p>
          <button type="button" className="link-button" onClick={() => setPendingToken(null)}>
            Back to login
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <h2>Login</h2>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
      <p>
        <Link to="/forgot-password">Forgot username or password?</Link>
      </p>
      <p>
        No account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}
