import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";

const REQUESTABLE_FIELDS = [
  { key: "name", label: "Name" },
  { key: "specialization", label: "Specialization" },
  { key: "hospital", label: "Hospital" },
];

// name / specialization / hospital all require admin approval - see the
// "Request a change" section. license_no can be set exactly once by the
// doctor; after that it's locked, and the only way to flag a mistake is
// the "Report incorrect license number" form below - admin still has to
// apply the actual fix manually, this just gets it in front of them.
export default function DoctorProfileForm() {
  const [profile, setProfile] = useState(null);
  const [licenseNo, setLicenseNo] = useState("");
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const [requests, setRequests] = useState([]);
  const [field, setField] = useState("name");
  const [requestedValue, setRequestedValue] = useState("");
  const [reason, setReason] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [requestMsg, setRequestMsg] = useState("");
  const [requestErr, setRequestErr] = useState("");

  const [reportedLicense, setReportedLicense] = useState("");
  const [licenseReason, setLicenseReason] = useState("");
  const [reportingLicense, setReportingLicense] = useState(false);
  const [licenseReportMsg, setLicenseReportMsg] = useState("");
  const [licenseReportErr, setLicenseReportErr] = useState("");

  async function load() {
    setLoadingProfile(true);
    setError("");
    try {
      const [profileRes, requestsRes] = await Promise.all([
        apiFetch("/profile/doctor"),
        apiFetch("/profile/change-requests"),
      ]);
      setProfile(profileRes);
      setLicenseNo(profileRes.license_no || "");
      setRequests(requestsRes || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingProfile(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const licenseLocked = Boolean(profile?.license_no);

  async function handleSaveLicense(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await apiFetch("/profile/doctor", {
        method: "PATCH",
        body: { license_no: licenseNo },
      });
      setSuccess("License number saved.");
      setTimeout(() => navigate("/doctor"), 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function pendingRequestFor(key) {
    return requests.find((r) => r.field === key && r.status === "pending");
  }

  async function handleRequestChange(e) {
    e.preventDefault();
    setRequestMsg("");
    setRequestErr("");
    setRequesting(true);
    try {
      const res = await apiFetch("/profile/change-request", {
        method: "POST",
        body: { field, requested_value: requestedValue, reason: reason || null },
      });
      setRequestMsg(res.message);
      setRequestedValue("");
      setReason("");
      await load();
    } catch (err) {
      setRequestErr(err.message);
    } finally {
      setRequesting(false);
    }
  }

  async function handleReportLicense(e) {
    e.preventDefault();
    setLicenseReportMsg("");
    setLicenseReportErr("");
    setReportingLicense(true);
    try {
      const res = await apiFetch("/profile/change-request", {
        method: "POST",
        body: {
          field: "license_no",
          requested_value: reportedLicense,
          reason: licenseReason || null,
        },
      });
      setLicenseReportMsg(res.message);
      setReportedLicense("");
      setLicenseReason("");
      await load();
    } catch (err) {
      setLicenseReportErr(err.message);
    } finally {
      setReportingLicense(false);
    }
  }

  if (loadingProfile) return <div className="page">Loading...</div>;

  const activeFieldPending = pendingRequestFor(field);
  const pendingLicenseReport = pendingRequestFor("license_no");

  return (
    <div className="page">
      <p>
        <Link to="/doctor">&larr; Back to dashboard</Link>
      </p>
      <h2>Doctor Profile</h2>

      <div className="card">
        <p><strong>Name:</strong> {profile?.name}</p>
        <p><strong>Email:</strong> {profile?.email}</p>
        <p><strong>Specialization:</strong> {profile?.specialization || "—"}</p>
        <p><strong>Hospital:</strong> {profile?.hospital || "—"}</p>
        <p className="hint">
          Name, specialization, and hospital changes need admin approval -
          use the "Request a change" form below.
        </p>
      </div>

      <h3>License number</h3>
      {licenseLocked ? (
        <>
          <p className="hint">
            License number is set to <strong>{profile.license_no}</strong> and
            can't be changed by you.
          </p>

          <h4>Report incorrect license number</h4>
          {pendingLicenseReport ? (
            <p className="hint">
              You already reported this as "{pendingLicenseReport.requested_value}"
              - admin hasn't resolved it yet.
            </p>
          ) : (
            <form onSubmit={handleReportLicense} className="form">
              <label>
                What it should be
                <input
                  value={reportedLicense}
                  onChange={(e) => setReportedLicense(e.target.value)}
                  required
                />
              </label>
              <label>
                Note (optional)
                <input value={licenseReason} onChange={(e) => setLicenseReason(e.target.value)} />
              </label>
              {licenseReportErr && <p className="error">{licenseReportErr}</p>}
              {licenseReportMsg && <p className="success">{licenseReportMsg}</p>}
              <button type="submit" disabled={reportingLicense}>
                {reportingLicense ? "Reporting..." : "Report to Admin"}
              </button>
            </form>
          )}
        </>
      ) : (
        <form onSubmit={handleSaveLicense} className="form">
          <label>
            License Number
            <input value={licenseNo} onChange={(e) => setLicenseNo(e.target.value)} required />
          </label>
          <p className="hint">
            You can only set this once - double check it before saving.
          </p>
          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}
          <button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save License Number"}
          </button>
        </form>
      )}

      <h3>Request a change</h3>
      <form onSubmit={handleRequestChange} className="form">
        <label>
          Field
          <select value={field} onChange={(e) => setField(e.target.value)}>
            {REQUESTABLE_FIELDS.map((f) => (
              <option key={f.key} value={f.key}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
        {activeFieldPending ? (
          <p className="hint">
            You already have a pending request to change this to "
            {activeFieldPending.requested_value}" - waiting on admin.
          </p>
        ) : (
          <>
            <label>
              New value
              <input value={requestedValue} onChange={(e) => setRequestedValue(e.target.value)} required />
            </label>
            <label>
              Reason (optional)
              <input value={reason} onChange={(e) => setReason(e.target.value)} />
            </label>
            {requestErr && <p className="error">{requestErr}</p>}
            {requestMsg && <p className="success">{requestMsg}</p>}
            <button type="submit" disabled={requesting}>
              {requesting ? "Submitting..." : "Submit Request"}
            </button>
          </>
        )}
      </form>

      {requests.length > 0 && (
        <>
          <h4>Your requests</h4>
          <table>
            <thead>
              <tr>
                <th>Field</th>
                <th>Requested Value</th>
                <th>Status</th>
                <th>Admin Note</th>
                <th>Requested At</th>
              </tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.field}</td>
                  <td>{r.requested_value}</td>
                  <td>{r.status}</td>
                  <td>{r.admin_note || "—"}</td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
