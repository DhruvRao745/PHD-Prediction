import { useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";
import { useAuth } from "../auth/AuthContext.jsx";
import Greeting from "../components/Greeting.jsx";
import Avatar from "../components/Avatar.jsx";
import EmptyState from "../components/EmptyState.jsx";
import { useToast } from "../components/Toast.jsx";

export default function AdminDashboard() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [deletedAssignments, setDeletedAssignments] = useState([]);
  const [deletedPredictions, setDeletedPredictions] = useState([]);
  const [requests, setRequests] = useState([]);
  const [profileRequests, setProfileRequests] = useState([]);
  const [activityLog, setActivityLog] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [assignDoctorId, setAssignDoctorId] = useState("");
  const [assignPatientId, setAssignPatientId] = useState("");
  const [assignDisease, setAssignDisease] = useState("");
  const [assigning, setAssigning] = useState(false);

  const [licenseDoctorId, setLicenseDoctorId] = useState("");
  const [licenseValue, setLicenseValue] = useState("");
  const [savingLicense, setSavingLicense] = useState(false);

  const [riskPatientId, setRiskPatientId] = useState("");
  const [riskSummary, setRiskSummary] = useState(null);
  const [loadingRiskSummary, setLoadingRiskSummary] = useState(false);
  const [riskSummaryError, setRiskSummaryError] = useState("");

  const [analytics, setAnalytics] = useState(null);

  const [activeSection, setActiveSection] = useState("overview");

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [
        doctorsRes,
        patientsRes,
        assignmentsRes,
        deletedAssignRes,
        deletedPredRes,
        requestsRes,
        profileRequestsRes,
        activityLogRes,
        analyticsRes,
      ] = await Promise.all([
        apiFetch("/admin/doctors"),
        apiFetch("/admin/patients"),
        apiFetch("/admin/assignments"),
        apiFetch("/admin/assignments/deleted"),
        apiFetch("/admin/predictions/deleted"),
        apiFetch("/admin/reassignment-requests"),
        apiFetch("/admin/profile-change-requests"),
        apiFetch("/admin/activity-log"),
        apiFetch("/admin/analytics"),
      ]);
      setDoctors(doctorsRes);
      setPatients(patientsRes);
      setAssignments(assignmentsRes);
      setDeletedAssignments(deletedAssignRes);
      setDeletedPredictions(deletedPredRes);
      setRequests(requestsRes);
      setProfileRequests(profileRequestsRes);
      setActivityLog(activityLogRes);
      setAnalytics(analyticsRes);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  function flash(fn) {
    return async (...args) => {
      try {
        const res = await fn(...args);
        showToast(res?.message || "Done");
        await loadAll();
      } catch (err) {
        showToast(err.message, "error");
      }
    };
  }

  async function handleAssign(e) {
    e.preventDefault();
    setAssigning(true);
    try {
      const res = await apiFetch("/admin/assign-patient", {
        method: "POST",
        body: {
          doctor_id: Number(assignDoctorId),
          patient_id: Number(assignPatientId),
          disease: assignDisease,
        },
      });
      showToast(res.message);
      await loadAll();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setAssigning(false);
    }
  }

  // Wraps a flash()-created handler with a confirmation prompt first -
  // for actions that are destructive or hard/impossible to undo. If the
  // user cancels, the request never fires.
  function withConfirm(handler, message) {
    return async (...args) => {
      if (!window.confirm(message)) return;
      await handler(...args);
    };
  }

  const handleUnassign = withConfirm(
    flash((id) => apiFetch(`/admin/unassign/${id}`, { method: "DELETE" })),
    "Unassign this doctor from this patient?"
  );

  const handleRestoreAssignment = flash((id) =>
    apiFetch(`/admin/assignments/${id}/restore`, { method: "PATCH" })
  );

  const handlePurgeAssignment = withConfirm(
    flash((id) => apiFetch(`/admin/assignments/${id}/permanent`, { method: "DELETE" })),
    "Permanently delete this assignment? This cannot be undone."
  );

  const handleRestorePrediction = flash((id) =>
    apiFetch(`/admin/predictions/${id}/restore`, { method: "PATCH" })
  );

  const handlePurgePrediction = withConfirm(
    flash((id) => apiFetch(`/admin/predictions/${id}/permanent`, { method: "DELETE" })),
    "Permanently delete this prediction? This cannot be undone."
  );

  // Denials always ask for a reason - the person on the other end has a
  // right to know why, not just see "denied". Approvals can optionally
  // get a note too but aren't forced to.
  function promptForNote(status) {
    if (status !== "denied") return null;
    return window.prompt("Reason for denial (the requester will see this):") || null;
  }

  const handleResolveRequest = flash((id, status) =>
    apiFetch(`/admin/reassignment-requests/${id}`, {
      method: "PATCH",
      body: { status, note: promptForNote(status) },
    })
  );

  const handleResolveProfileRequest = flash((id, status) =>
    apiFetch(`/admin/profile-change-requests/${id}`, {
      method: "PATCH",
      body: { status, note: promptForNote(status) },
    })
  );

  async function handleCorrectLicense(e) {
    e.preventDefault();
    setSavingLicense(true);
    try {
      const res = await apiFetch(`/admin/doctors/${licenseDoctorId}/license`, {
        method: "PATCH",
        body: { license_no: licenseValue },
      });
      showToast(res.message);
      setLicenseValue("");
      await loadAll();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setSavingLicense(false);
    }
  }

  async function handleLoadRiskSummary(patientId) {
    setRiskPatientId(patientId);
    setRiskSummary(null);
    setRiskSummaryError("");
    if (!patientId) return;
    setLoadingRiskSummary(true);
    try {
      const res = await apiFetch(`/admin/patients/${patientId}/risk-summary`);
      setRiskSummary(res);
    } catch (err) {
      setRiskSummaryError(err.message);
    } finally {
      setLoadingRiskSummary(false);
    }
  }

  if (loading) return <div className="page">Loading...</div>;

  const pendingRequestCount = requests.length;
  const pendingProfileCount = profileRequests.length;
  const deletedCount = deletedAssignments.length + deletedPredictions.length;
  const needsAttention = pendingRequestCount + pendingProfileCount;

  const NAV_ITEMS = [
    { id: "overview", label: "Overview" },
    { id: "active", label: "Active assignments", count: assignments.length },
    { id: "deleted", label: "Deleted / restore", count: deletedCount },
    { id: "reassign", label: "Reassignment requests", badge: pendingRequestCount },
    { id: "profile", label: "Profile requests", badge: pendingProfileCount },
    { id: "risk", label: "Risk overview" },
    { id: "analytics", label: "Analytics" },
    { id: "activity", label: "Activity log" },
  ];

  const summaryParts = [];
  if (pendingRequestCount > 0) {
    summaryParts.push(`${pendingRequestCount} reassignment request${pendingRequestCount === 1 ? "" : "s"}`);
  }
  if (pendingProfileCount > 0) {
    summaryParts.push(`${pendingProfileCount} profile request${pendingProfileCount === 1 ? "" : "s"}`);
  }
  const summary =
    summaryParts.length === 0
      ? "Everything's caught up - no pending requests right now."
      : `You have ${summaryParts.join(" and ")} waiting for review.`;

  const QUICK_ACTIONS = [
    { label: "Assign a patient", goto: "overview" },
    { label: "Review reassignment requests", goto: "reassign" },
    { label: "Review profile requests", goto: "profile" },
    { label: "View active assignments", goto: "active" },
    { label: "Deleted / restore", goto: "deleted" },
  ];

  return (
    <div className="page" style={{ maxWidth: 1000 }}>
      <Greeting name={user?.username || "Admin"} summary={summary} />

      {error && <p className="error">{error}</p>}

      <div className="quick-actions">
        {QUICK_ACTIONS.map((qa) => (
          <button key={qa.goto} type="button" onClick={() => setActiveSection(qa.goto)}>
            {qa.label}
          </button>
        ))}
      </div>

      <div className="admin-shell">
        <nav className="admin-sidebar">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`admin-nav-item${activeSection === item.id ? " active" : ""}`}
              onClick={() => setActiveSection(item.id)}
            >
              {item.label}
              {!!item.badge && <span className="nav-badge">{item.badge}</span>}
              {!item.badge && item.count != null && <span className="nav-count">{item.count}</span>}
            </button>
          ))}
        </nav>

        <div className="admin-content">
          <div className="metrics-row">
            <div className="metric-card">
              <p className="metric-label">Doctors</p>
              <p className="metric-value">{doctors.length}</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Patients</p>
              <p className="metric-value">{patients.length}</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Active assignments</p>
              <p className="metric-value">{assignments.length}</p>
            </div>
            <div className={`metric-card${needsAttention > 0 ? " warning" : ""}`}>
              <p className="metric-label">Needs attention</p>
              <p className="metric-value">{needsAttention}</p>
            </div>
          </div>

          {activeSection === "overview" && (
      <>
      <h3>Assign a patient to a doctor</h3>
      <form
        onSubmit={handleAssign}
        className="form"
        style={{ flexDirection: "row", alignItems: "flex-end", gap: "0.5rem", maxWidth: "none" }}
      >
        <label style={{ flex: 1 }}>
          Doctor
          <select value={assignDoctorId} onChange={(e) => setAssignDoctorId(e.target.value)} required>
            <option value="">Select a doctor</option>
            {doctors.map((d) => (
              <option key={d.doctor_id} value={d.doctor_id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ flex: 1 }}>
          Patient
          <select value={assignPatientId} onChange={(e) => setAssignPatientId(e.target.value)} required>
            <option value="">Select a patient</option>
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ flex: 1 }}>
          Disease
          <select value={assignDisease} onChange={(e) => setAssignDisease(e.target.value)} required>
            <option value="">Select a disease</option>
            {Object.entries(DISEASES).map(([key, d]) => (
              <option key={key} value={key}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={assigning}>
          {assigning ? "Assigning..." : "Assign"}
        </button>
      </form>
      <p className="hint">
        Each assignment is scoped to one disease - the doctor will only see
        that patient's data for the disease picked here, not their full
        history. Assign the same doctor again for a different disease if
        needed.
      </p>

      <h3>Correct a doctor's license number</h3>
      <p className="hint">
        Doctors can only set their license number once and can never edit
        it themselves afterward - use this to fix a typo.
      </p>
      <form
        onSubmit={handleCorrectLicense}
        className="form"
        style={{ flexDirection: "row", alignItems: "flex-end", gap: "0.5rem", maxWidth: "none" }}
      >
        <label style={{ flex: 1 }}>
          Doctor
          <select value={licenseDoctorId} onChange={(e) => setLicenseDoctorId(e.target.value)} required>
            <option value="">Select a doctor</option>
            {doctors.map((d) => (
              <option key={d.doctor_id} value={d.doctor_id}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ flex: 1 }}>
          Correct License Number
          <input value={licenseValue} onChange={(e) => setLicenseValue(e.target.value)} required />
        </label>
        <button type="submit" disabled={savingLicense}>
          {savingLicense ? "Saving..." : "Save"}
        </button>
      </form>
      </>
          )}

          {activeSection === "active" && (
      <>
      <h3>Active assignments</h3>
      {assignments.length === 0 && (
        <EmptyState
          title="No active assignments"
          hint="Assign a doctor to a patient above to get started."
        />
      )}
      {assignments.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Doctor</th>
              <th>Patient</th>
              <th>Disease</th>
              <th>Status</th>
              <th>Assigned At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={a.id}>
                <td>
                  <div className="person-row">
                    <Avatar name={a.doctor_username} size={26} />
                    <span>{a.doctor_username}</span>
                  </div>
                </td>
                <td>
                  <div className="person-row">
                    <Avatar name={a.patient_username} size={26} />
                    <span>{a.patient_username}</span>
                  </div>
                </td>
                <td>{DISEASES[a.disease]?.label || a.disease}</td>
                <td><span className="status-chip success">Active</span></td>
                <td>{new Date(a.assigned_at).toLocaleString()}</td>
                <td>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn-sm danger"
                      onClick={() => handleUnassign(a.id)}
                    >
                      Unassign
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </>
          )}

          {activeSection === "reassign" && (
      <>
      <h3>Pending reassignment requests</h3>
      {requests.length === 0 && (
        <EmptyState title="No pending reassignment requests" hint="You're all caught up." />
      )}
      {requests.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Doctor</th>
              <th>Disease</th>
              <th>Reason</th>
              <th>Requested At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {requests.map((r) => (
              <tr key={r.id}>
                <td>{r.patient_username}</td>
                <td>{r.doctor_username || "—"}</td>
                <td>{DISEASES[r.disease]?.label || r.disease}</td>
                <td>{r.reason || "—"}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn-sm success"
                      onClick={() => handleResolveRequest(r.id, "approved")}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="btn-sm danger"
                      onClick={() => handleResolveRequest(r.id, "denied")}
                    >
                      Deny
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </>
          )}

          {activeSection === "profile" && (
      <>
      <h3>Pending profile change requests</h3>
      <p className="hint">
        Name (patient/doctor) and specialization/hospital (doctor) changes
        land here for approval instead of being self-edited. Approving one
        writes the requested value straight into their profile - except
        "license_no" rows, which are just reports: approving/denying only
        closes the ticket, it does NOT change the license number. Use the
        "Correct a doctor's license number" form in the Overview section to
        actually apply that fix.
      </p>
      {profileRequests.length === 0 && (
        <EmptyState title="No pending profile requests" hint="You're all caught up." />
      )}
      {profileRequests.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Field</th>
              <th>Requested Value</th>
              <th>Reason</th>
              <th>Requested At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {profileRequests.map((r) => (
              <tr key={r.id}>
                <td>{r.username}</td>
                <td>{r.role}</td>
                <td>{r.field}</td>
                <td>{r.requested_value}</td>
                <td>{r.reason || "—"}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn-sm success"
                      onClick={() => handleResolveProfileRequest(r.id, "approved")}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="btn-sm danger"
                      onClick={() => handleResolveProfileRequest(r.id, "denied")}
                    >
                      Deny
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </>
          )}

          {activeSection === "deleted" && (
      <>
      <h3>Soft-deleted assignments</h3>
      {deletedAssignments.length === 0 && <EmptyState title="Nothing here" hint="Unassigned doctor-patient links show up here for restore or permanent deletion." />}
      {deletedAssignments.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Doctor</th>
              <th>Patient</th>
              <th>Disease</th>
              <th>Deleted At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {deletedAssignments.map((a) => (
              <tr key={a.id}>
                <td>{a.doctor_username}</td>
                <td>{a.patient_username}</td>
                <td>{DISEASES[a.disease]?.label || a.disease}</td>
                <td>{new Date(a.deleted_at).toLocaleString()}</td>
                <td>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn-sm success"
                      onClick={() => handleRestoreAssignment(a.id)}
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      className="btn-sm danger"
                      onClick={() => handlePurgeAssignment(a.id)}
                    >
                      Delete forever
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Soft-deleted predictions</h3>
      {deletedPredictions.length === 0 && <EmptyState title="Nothing here" hint="Soft-deleted predictions show up here for restore or permanent deletion." />}
      {deletedPredictions.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th>Disease</th>
              <th>Risk</th>
              <th>Deleted At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {deletedPredictions.map((p) => (
              <tr key={p.id}>
                <td>
                  {p.account_username} ({p.account_role})
                </td>
                <td>{DISEASES[p.disease]?.label || p.disease}</td>
                <td>{p.risk_level} ({p.probability})</td>
                <td>{new Date(p.deleted_at).toLocaleString()}</td>
                <td>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn-sm success"
                      onClick={() => handleRestorePrediction(p.id)}
                    >
                      Restore
                    </button>
                    <button
                      type="button"
                      className="btn-sm danger"
                      onClick={() => handlePurgePrediction(p.id)}
                    >
                      Delete forever
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </>
          )}

          {activeSection === "risk" && (
      <>
      <h3>Cross-disease risk overview</h3>
      <p className="hint">
        Pick a patient to see their most recent result across all 4 diseases in one place.
      </p>
      <label style={{ display: "block", maxWidth: 320, marginBottom: "1rem" }}>
        Patient
        <select value={riskPatientId} onChange={(e) => handleLoadRiskSummary(e.target.value)}>
          <option value="">Select a patient</option>
          {patients.map((p) => (
            <option key={p.patient_id} value={p.patient_id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>

      {loadingRiskSummary && <p>Loading...</p>}
      {riskSummaryError && <p className="error">{riskSummaryError}</p>}

      {riskSummary && (
        <>
          <h4>{riskSummary.patient_name}</h4>
          <div className="metrics-row">
            {riskSummary.summary.map((s) => (
              <div key={s.disease} className="metric-card">
                <p className="metric-label">{DISEASES[s.disease]?.label || s.disease}</p>
                {s.risk ? (
                  <>
                    <span className={`status-chip ${s.risk === "High Risk" ? "danger" : "success"}`}>
                      {s.risk}
                    </span>
                    <p className="hint" style={{ margin: "0.35rem 0 0" }}>
                      {new Date(s.date).toLocaleDateString()}
                    </p>
                  </>
                ) : (
                  <span className="hint">No data yet</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
      </>
          )}

          {activeSection === "analytics" && (
      <>
      <h3>Analytics</h3>
      <p className="hint">
        A system-wide view - not scoped to any one patient or doctor.
      </p>

      {!analytics && <p>Loading...</p>}

      {analytics && (
        <>
          <h4>Predictions run per disease</h4>
          {analytics.predictions_per_disease.length === 0 ? (
            <EmptyState title="No predictions yet" hint="Charts will fill in once patients start running predictions." />
          ) : (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart
                  data={analytics.predictions_per_disease.map((d) => ({
                    label: DISEASES[d.disease]?.label || d.disease,
                    count: d.count,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Predictions" fill="#4a90d9" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <h4 style={{ marginTop: "2rem" }}>Risk level distribution per disease</h4>
          {analytics.risk_distribution.length === 0 ? (
            <EmptyState title="No predictions yet" hint="Charts will fill in once patients start running predictions." />
          ) : (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart
                  data={analytics.risk_distribution.map((d) => ({
                    label: DISEASES[d.disease]?.label || d.disease,
                    "High Risk": d.high_risk,
                    "Low Risk": d.low_risk,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="High Risk" fill="#c0392b" />
                  <Bar dataKey="Low Risk" fill="#27ae60" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <h4 style={{ marginTop: "2rem" }}>New signups (last 30 days)</h4>
          {analytics.signups_over_time.length === 0 ? (
            <EmptyState title="No new signups yet" hint="This fills in as new patients and doctors register." />
          ) : (
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={analytics.signups_over_time}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="patient" name="Patients" stroke="#4a90d9" />
                  <Line type="monotone" dataKey="doctor" name="Doctors" stroke="#8e44ad" />
                  <Line type="monotone" dataKey="admin" name="Admins" stroke="#95a5a6" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
      </>
          )}

          {activeSection === "activity" && (
      <>
      <h3>Activity log</h3>
      <p className="hint">
        A permanent record of who did what, across the whole system - newest first,
        capped at the last 200 actions.
      </p>
      {activityLog.length === 0 && (
        <EmptyState title="Nothing logged yet" hint="Actions you take will start showing up here." />
      )}
      {activityLog.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Who</th>
              <th>Action</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            {activityLog.map((a) => (
              <tr key={a.id}>
                <td>
                  <div className="person-row">
                    <Avatar name={a.actor_username} size={26} />
                    <div className="person-meta">
                      <span>{a.actor_username}</span>
                      <span className="person-sub">{a.actor_role}</span>
                    </div>
                  </div>
                </td>
                <td>{a.description}</td>
                <td>{new Date(a.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      </>
          )}
        </div>
      </div>
    </div>
  );
}
