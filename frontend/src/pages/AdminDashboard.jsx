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

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionError, setActionError] = useState("");

  const [assignDoctorId, setAssignDoctorId] = useState("");
  const [assignPatientId, setAssignPatientId] = useState("");
  const [assigning, setAssigning] = useState(false);

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [doctorsRes, patientsRes, assignmentsRes, deletedAssignRes, deletedPredRes, requestsRes] =
        await Promise.all([
          apiFetch("/admin/doctors"),
          apiFetch("/admin/patients"),
          apiFetch("/admin/assignments"),
          apiFetch("/admin/assignments/deleted"),
          apiFetch("/admin/predictions/deleted"),
          apiFetch("/admin/reassignment-requests"),
        ]);
      setDoctors(doctorsRes);
      setPatients(patientsRes);
      setAssignments(assignmentsRes);
      setDeletedAssignments(deletedAssignRes);
      setDeletedPredictions(deletedPredRes);
      setRequests(requestsRes);
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

  const handleUnassign = flash((doctorId, patientId) =>
    apiFetch(`/admin/unassign/${doctorId}/${patientId}`, { method: "DELETE" })
  );

  const handleRestoreAssignment = flash((doctorId, patientId) =>
    apiFetch(`/admin/assignments/${doctorId}/${patientId}/restore`, { method: "PATCH" })
  );

  const handlePurgeAssignment = flash((doctorId, patientId) =>
    apiFetch(`/admin/assignments/${doctorId}/${patientId}/permanent`, { method: "DELETE" })
  );

  const handleRestorePrediction = flash((id) =>
    apiFetch(`/admin/predictions/${id}/restore`, { method: "PATCH" })
  );

  const handlePurgePrediction = flash((id) =>
    apiFetch(`/admin/predictions/${id}/permanent`, { method: "DELETE" })
  );

  const handleResolveRequest = flash((id, status) =>
    apiFetch(`/admin/reassignment-requests/${id}`, {
      method: "PATCH",
      body: { status },
    })
  );

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
        <button type="submit" disabled={assigning}>
          {assigning ? "Assigning..." : "Assign"}
        </button>
      </form>

      <h3>Active assignments</h3>
      {assignments.length === 0 && <p>No active assignments.</p>}
      {assignments.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Doctor</th>
              <th>Patient</th>
              <th>Assigned At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((a) => (
              <tr key={`${a.doctor_id}-${a.patient_id}`}>
                <td>{a.doctor_username} (ID: {a.doctor_id})</td>
                <td>{a.patient_username} (ID: {a.patient_id})</td>
                <td>{new Date(a.assigned_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleUnassign(a.doctor_id, a.patient_id)}
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
              <th>Current Doctor</th>
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

      <h3>Soft-deleted assignments</h3>
      {deletedAssignments.length === 0 && <p>None.</p>}
      {deletedAssignments.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Doctor</th>
              <th>Patient</th>
              <th>Deleted At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {deletedAssignments.map((a) => (
              <tr key={`${a.doctor_id}-${a.patient_id}`}>
                <td>{a.doctor_username} (ID: {a.doctor_id})</td>
                <td>{a.patient_username} (ID: {a.patient_id})</td>
                <td>{new Date(a.deleted_at).toLocaleString()}</td>
                <td>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handleRestoreAssignment(a.doctor_id, a.patient_id)}
                  >
                    Restore
                  </button>{" "}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => handlePurgeAssignment(a.doctor_id, a.patient_id)}
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
              <th>Patient</th>
              <th>Disease</th>
              <th>Risk</th>
              <th>Deleted At</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {deletedPredictions.map((p) => (
              <tr key={p.id}>
                <td>{p.patient_username} (ID: {p.patient_id})</td>
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
