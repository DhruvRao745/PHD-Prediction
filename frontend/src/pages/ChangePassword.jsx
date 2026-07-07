import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { getDashboardPath } from "../utils/roles.js";
import TwoFactorSettings from "../components/TwoFactorSettings.jsx";

// Works for any logged-in role (patient, doctor, admin) - password and
// email both live on the Account itself, not a role-specific profile.
// This is also the only place an admin can fix up their email, since
// admin has no separate profile page the way patient/doctor do.
//
// TEMP: the `minLength={6}` constraint on the new-password/confirm
// inputs below was removed for testing convenience, matching the
// matching check disabled in app/auth/routes.py's change_password
// route. RE-ADD `minLength={6}` to both password inputs before launch.
export default function ChangePassword() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const [email, setEmail] = useState(user?.email || "");
  const [emailError, setEmailError] = useState("");
  const [emailSuccess, setEmailSuccess] = useState("");
  const [savingEmail, setSavingEmail] = useState(false);

  // user loads asynchronously (AuthContext fetches /auth/me after this
  // page may already have mounted) - sync the field once it arrives.
  useEffect(() => {
    if (user?.email) setEmail(user.email);
  }, [user]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/auth/change-password", {
        method: "POST",
        body: {
          current_password: currentPassword,
          new_password: newPassword,
        },
      });
      setSuccess(res.message);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => navigate(getDashboardPath(user?.role)), 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleEmailSubmit(e) {
    e.preventDefault();
    setEmailError("");
    setEmailSuccess("");
    setSavingEmail(true);
    try {
      const res = await apiFetch("/auth/account/email", {
        method: "PATCH",
        body: { email },
      });
      setEmailSuccess(res.message);
    } catch (err) {
      setEmailError(err.message);
    } finally {
      setSavingEmail(false);
    }
  }

  return (
    <div className="page">
      <h2>Account Settings</h2>

      <h3>Email</h3>
      <p className="hint">
        Used for password reset links - make sure this is a real inbox
        you can check.
      </p>
      <form onSubmit={handleEmailSubmit} className="form">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        {emailError && <p className="error">{emailError}</p>}
        {emailSuccess && <p className="success">{emailSuccess}</p>}
        <button type="submit" disabled={savingEmail}>
          {savingEmail ? "Saving..." : "Save Email"}
        </button>
      </form>

      <h3>Change Password</h3>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Current Password
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
        </label>
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
          {loading ? "Saving..." : "Change Password"}
        </button>
      </form>

      {user?.role === "admin" && (
        <>
          <h3>Two-Factor Authentication</h3>
          <TwoFactorSettings />
        </>
      )}
    </div>
  );
}
