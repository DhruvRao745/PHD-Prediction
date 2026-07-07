import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";

// TEMP: minLength={6} removed on both password inputs below, matching
// the matching check disabled in app/auth/routes.py's reset_password
// route. RE-ADD minLength={6} to both before launch.
export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!token) {
      setError("Missing or invalid reset link - request a new one.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/auth/reset-password", {
        method: "POST",
        body: { token, new_password: newPassword },
        auth: false,
      });
      setSuccess(res.message);
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="page">
        <h2>Reset password</h2>
        <p className="error">
          This link is missing its reset code. Request a new one from the{" "}
          <Link to="/forgot-password">forgot password page</Link>.
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <h2>Set a new password</h2>
      <form onSubmit={handleSubmit} className="form">
        <label>
          New Password
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
        </label>
        <label>
          Confirm New Password
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Saving..." : "Reset Password"}
        </button>
      </form>
    </div>
  );
}
