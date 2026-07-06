import { useEffect, useState } from "react";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";

export default function AdminDashboard() {
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [deletedAssignments, setDeletedAssignments] = useState([]);
  const [deletedPredictions, setDeletedPredictions] = useState([]);
  const [requests, setRequests] = useState([]);
  const [profileRequests, setProfileRequests] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState("");

  const [assignDoctorId, setAssignDoctorId] = useState("");
  const [assignPatientId, setAssignPatientId] = useState("");
  const [assignDisease, setAssignDisease] = useState("");
  const [assigning, setAssigning] = useState(false);

  const [licenseDoctorId, setLicenseDoctorId] = useState("");
  const [licenseValue, setLicenseValue] = useState("");
  const [savingLicense, setSavingLicense] = useState(false);

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
      ] = await Promise.all([
        apiFetch("/admin/doctors"),
        apiFetch("/admin/patients"),
        apiFetch("/admin/assignments"),
        apiFetch("/admin/assignments/deleted"),
        apiFetch("/admin/predictions/deleted"),
        apiFetch("/admin/reassignment-requests"),
        apiFetch("/admin/profile-change-requests"),
      ]);
      setDoctors(doctorsRes);
      setPatients(patientsRes);
      setAssignments(assignmentsRes);
      setDeletedAssignments(deletedAssignRes);
      setDeletedPredictions(deletedPredRes);
      setRequests(requestsRes);
      setProfileRequests(profileRequestsRes);
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
      setActionMessage("");
      setActionError("");
      try {
        const res = await fn(...args);
        if (res?.message) setActionMessage(res.message);
        await loadAll();
      } catch (err) {
        setActionError(err.message);
      }
    };
  }

  async function handleAssign(e) {
    e.preventDefault();
    setActionMessage("");
    setActionError("");
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
      setActionMessage(res.message);
      await loadAll();
    } catch (err) {
      setActionError(err.message);
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
    setActionMessage("");
    setActionError("");
    setSavingLicense(true);
    try {
      const res = await apiFetch(`/admin/doctors/${licenseDoctorId}/license`, {
        method: "PATCH",
        body: { license_no: licenseValue },
      });
      setActionMessage(res.message);
      setLicenseValue("");
      await loadAll();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSavingLicense(false);
    }
  }

  if (loading) return <div className="page">Loading...</div>;

  return (
    <div className="page" style={{ maxWidth: 900 }}>
      <h2>Admin Dashboard</h2>

      {error && <p className="error">{error}</p>}
      {actionMessage && <p className="success">{actionMessage}</p>}
      {actionError && <p className="error">{actionError}</p>}

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
                {d.name} (ID: {d.doctor_id})
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
                {p.name} (ID: {p.patient_id})
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

      <h3>Active assignments</h3>
      {assignments.length === 0 && <p>No active assignments.</p>}
      {assignments.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Doctor</th>
              <th>Patient</th>
              <th>Disease</th>
              <th>Assigned At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={a.id}>
                <td>{a.doctor_username} (ID: {a.doctor_id})</td>
                <td>{a.patient_username} (ID: {a.patient_id})</td>
                <td>{DISEASES[a.disease]?.label || a.disease}</td>
                <td>{new Date(a.assigned_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleUnassign(a.id)}
                  >
                    Unassign
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Pending reassignment requests</h3>
      {requests.length === 0 && <p>No pending requests.</p>}
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
                <td>{r.patient_username} (ID: {r.patient_id})</td>
                <td>{r.doctor_username ? `${r.doctor_username} (ID: ${r.doctor_id})` : "—"}</td>
                <td>{DISEASES[r.disease]?.label || r.disease}</td>
                <td>{r.reason || "—"}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleResolveRequest(r.id, "approved")}
                  >
                    Approve
                  </button>{" "}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleResolveRequest(r.id, "denied")}
                  >
                    Deny
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Pending profile change requests</h3>
      <p className="hint">
        Name (patient/doctor) and specialization/hospital (doctor) changes
        land here for approval instead of being self-edited. Approving one
        writes the requested value straight into their profile - except
        "license_no" rows, which are just reports: approving/denying only
        closes the ticket, it does NOT change the license number. Use the
        "Correct a doctor's license number" form below to actually apply
        that fix.
      </p>
      {profileRequests.length === 0 && <p>No pending requests.</p>}
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
                <td>{r.username} (ID: {r.account_id})</td>
                <td>{r.role}</td>
                <td>{r.field}</td>
                <td>{r.requested_value}</td>
                <td>{r.reason || "—"}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleResolveProfileRequest(r.id, "approved")}
                  >
                    Approve
                  </button>{" "}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleResolveProfileRequest(r.id, "denied")}
                  >
                    Deny
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

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
                {d.name} (ID: {d.doctor_id})
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

      <h3>Soft-deleted assignments</h3>
      {deletedAssignments.length === 0 && <p>None.</p>}
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
                <td>{a.doctor_username} (ID: {a.doctor_id})</td>
                <td>{a.patient_username} (ID: {a.patient_id})</td>
                <td>{DISEASES[a.disease]?.label || a.disease}</td>
                <td>{new Date(a.deleted_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleRestoreAssignment(a.id)}
                  >
                    Restore
                  </button>{" "}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handlePurgeAssignment(a.id)}
                  >
                    Delete Forever
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Soft-deleted predictions</h3>
      {deletedPredictions.length === 0 && <p>None.</p>}
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
                  {p.account_username} (ID: {p.account_id}, {p.account_role})
                </td>
                <td>{DISEASES[p.disease]?.label || p.disease}</td>
                <td>{p.risk_level} ({p.probability})</td>
                <td>{new Date(p.deleted_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleRestorePrediction(p.id)}
                  >
                    Restore
                  </button>{" "}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handlePurgePrediction(p.id)}
                  >
                    Delete Forever
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
