import { useState } from "react";
import { apiFetch } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

// Admin-only 2FA management, embedded in Account Settings. Three states:
// off (show "Enable" button) -> setup in progress (QR + code input) ->
// on (show status + "Disable" form). Backup codes are only ever shown
// once, right after a successful setup.
export default function TwoFactorSettings() {
  const { user, refreshUser } = useAuth();

  const [settingUp, setSettingUp] = useState(false);
  const [qrCode, setQrCode] = useState("");
  const [secret, setSecret] = useState("");
  const [setupCode, setSetupCode] = useState("");
  const [setupError, setSetupError] = useState("");
  const [loadingSetup, setLoadingSetup] = useState(false);

  const [backupCodes, setBackupCodes] = useState(null);

  const [disablePassword, setDisablePassword] = useState("");
  const [disableError, setDisableError] = useState("");
  const [disabling, setDisabling] = useState(false);

  if (user?.role !== "admin") return null;

  async function handleStartSetup() {
    setSetupError("");
    setLoadingSetup(true);
    try {
      const res = await apiFetch("/auth/2fa/setup", { method: "POST" });
      setQrCode(res.qr_code);
      setSecret(res.secret);
      setSettingUp(true);
    } catch (err) {
      setSetupError(err.message);
    } finally {
      setLoadingSetup(false);
    }
  }

  async function handleVerifySetup(e) {
    e.preventDefault();
    setSetupError("");
    setLoadingSetup(true);
    try {
      const res = await apiFetch("/auth/2fa/verify-setup", {
        method: "POST",
        body: { code: setupCode },
      });
      setBackupCodes(res.backup_codes);
      setSettingUp(false);
      setSetupCode("");
      await refreshUser();
    } catch (err) {
      setSetupError(err.message);
    } finally {
      setLoadingSetup(false);
    }
  }

  async function handleDisable(e) {
    e.preventDefault();
    setDisableError("");
    setDisabling(true);
    try {
      await apiFetch("/auth/2fa/disable", {
        method: "POST",
        body: { password: disablePassword },
      });
      setDisablePassword("");
      setBackupCodes(null);
      await refreshUser();
    } catch (err) {
      setDisableError(err.message);
    } finally {
      setDisabling(false);
    }
  }

  // Right after enabling - show the backup codes exactly once, since
  // they're never retrievable again after this.
  if (backupCodes) {
    return (
      <div className="card">
        <h3>Save your backup codes</h3>
        <p className="hint">
          Each code works once, as a stand-in for your authenticator app if
          you ever lose access to it. Save these somewhere safe - they
          won't be shown again.
        </p>
        <ul style={{ fontFamily: "monospace", fontSize: "1.1em" }}>
          {backupCodes.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
        <button type="button" onClick={() => setBackupCodes(null)}>
          I've saved these
        </button>
      </div>
    );
  }

  if (settingUp) {
    return (
      <div className="card">
        <h3>Set up two-factor authentication</h3>
        <p className="hint">
          Scan this QR code with an authenticator app (Google Authenticator,
          Authy, Microsoft Authenticator, etc.), then enter the 6-digit
          code it shows to confirm.
        </p>
        {qrCode && <img src={qrCode} alt="2FA QR code" width={180} height={180} />}
        <p className="hint">
          Can't scan it? Enter this key manually: <code>{secret}</code>
        </p>
        <form onSubmit={handleVerifySetup} className="form">
          <label>
            6-digit code
            <input
              value={setupCode}
              onChange={(e) => setSetupCode(e.target.value)}
              autoFocus
              required
            />
          </label>
          {setupError && <p className="error">{setupError}</p>}
          <button type="submit" disabled={loadingSetup}>
            {loadingSetup ? "Verifying..." : "Verify & Enable"}
          </button>
        </form>
        <button type="button" className="link-button" onClick={() => setSettingUp(false)}>
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div>
      {user.totp_enabled ? (
        <>
          <p>
            <span className="status-chip success">Enabled</span>
          </p>
          <p className="hint">
            Confirm your password to turn two-factor authentication off.
          </p>
          <form onSubmit={handleDisable} className="form">
            <label>
              Current Password
              <input
                type="password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
                required
              />
            </label>
            {disableError && <p className="error">{disableError}</p>}
            <button type="submit" disabled={disabling}>
              {disabling ? "Disabling..." : "Disable 2FA"}
            </button>
          </form>
        </>
      ) : (
        <>
          <p className="hint">
            Adds a second step at login using an authenticator app on your
            phone - recommended for admin accounts.
          </p>
          {setupError && <p className="error">{setupError}</p>}
          <button type="button" onClick={handleStartSetup} disabled={loadingSetup}>
            {loadingSetup ? "Starting..." : "Enable 2FA"}
          </button>
        </>
      )}
    </div>
  );
}
