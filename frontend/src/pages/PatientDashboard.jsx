import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";

export default function PatientDashboard() {
  const [profile, setProfile] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteError, setDeleteError] = useState("");
  const [myDoctors, setMyDoctors] = useState([]);
  const [reassignChoice, setReassignChoice] = useState(""); // "doctorId:disease"
  const [reassignReason, setReassignReason] = useState("");
  const [reassignMessage, setReassignMessage] = useState("");
  const [reassignError, setReassignError] = useState("");
  const [requestingReassign, setRequestingReassign] = useState(false);
  const [reassignRequests, setReassignRequests] = useState([]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [res, requestsRes, doctorsRes] = await Promise.all([
        apiFetch("/dashboard/patient"),
        apiFetch("/reassignment-requests"),
        apiFetch("/my-doctors"),
      ]);
      setProfile(res.data.patient_profile);
      setPredictions(res.data.predictions || []);
      setReassignRequests(requestsRes || []);
      setMyDoctors(doctorsRes || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDelete(id) {
    if (!window.confirm("Delete this prediction? This can't be undone.")) return;
    setDeleteError("");
    try {
      await apiFetch(`/predictions/${id}`, { method: "DELETE" });
      setPredictions((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      setDeleteError(err.message);
    }
  }

  async function handleRequestReassignment(e) {
    e.preventDefault();
    setReassignMessage("");
    setReassignError("");
    setRequestingReassign(true);
    try {
      const [doctorId, disease] = reassignChoice.split(":");
      const res = await apiFetch("/reassignment-request", {
        method: "POST",
        body: {
          doctor_id: Number(doctorId),
          disease,
          reason: reassignReason || null,
        },
      });
      setReassignMessage(res.message);
      setReassignReason("");
      setReassignChoice("");
      const requestsRes = await apiFetch("/reassignment-requests");
      setReassignRequests(requestsRes || []);
    } catch (err) {
      setReassignError(err.message);
    } finally {
      setRequestingReassign(false);
    }
  }

  if (loading) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <h2>Patient Dashboard</h2>

      {error && <p className="error">{error}</p>}

      {profile && (
        <div className="card">
          <h3>{profile.name}</h3>
          <p>
            Age: {profile.age ?? "—"} | Gender: {profile.gender ?? "—"} | Height:{" "}
            {profile.height_cm ?? "—"} cm | Weight: {profile.weight_kg ?? "—"} kg
          </p>
          <Link to="/profile/patient">Edit profile</Link>
        </div>
      )}

      <h3>Your doctors</h3>
      {myDoctors.length === 0 && <p>No doctors assigned yet.</p>}
      {myDoctors.length > 0 && (
        <ul>
          {myDoctors.map((d) => (
            <li key={`${d.doctor_id}-${d.disease}`}>
              {d.name} — {DISEASES[d.disease]?.label || d.disease}
              {d.specialization ? ` (${d.specialization})` : ""}
            </li>
          ))}
        </ul>
      )}

      <h3>Run a prediction</h3>
      <div className="button-row">
        {Object.entries(DISEASES).map(([key, d]) => (
          <Link key={key} className="button-link" to={`/predict/${key}`}>
            {d.label}
          </Link>
        ))}
      </div>

      <h3>Recent predictions</h3>
      {deleteError && <p className="error">{deleteError}</p>}
      {predictions.length === 0 && <p>No predictions yet.</p>}
      {predictions.length > 0 && (
        <ul>
          {predictions.map((p) => (
            <li key={p.id}>
              {DISEASES[p.disease]?.label || p.disease}: {p.risk_level} (
              {p.probability}) — {new Date(p.created_at).toLocaleString()}{" "}
              <button type="button" className="link-button" onClick={() => handleDelete(p.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
      <p>
        <Link to="/history">View full history</Link>
      </p>

      <h3>Not happy with one of your doctors?</h3>
      <p className="hint">
        You can't unassign a doctor yourself - submit a request and admin
        will review it. Pick which doctor/disease you want to be
        reassigned away from - your other doctors, if any, aren't affected.
      </p>
      <form onSubmit={handleRequestReassignment} className="form">
        <label>
          Doctor
          <select
            value={reassignChoice}
            onChange={(e) => setReassignChoice(e.target.value)}
            required
          >
            <option value="">Select a doctor</option>
            {myDoctors.map((d) => (
              <option key={`${d.doctor_id}-${d.disease}`} value={`${d.doctor_id}:${d.disease}`}>
                {d.name} — {DISEASES[d.disease]?.label || d.disease}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reason (optional)
          <input
            value={reassignReason}
            onChange={(e) => setReassignReason(e.target.value)}
          />
        </label>
        {reassignError && <p className="error">{reassignError}</p>}
        {reassignMessage && <p className="success">{reassignMessage}</p>}
        <button type="submit" disabled={requestingReassign}>
          {requestingReassign ? "Submitting..." : "Request Reassignment"}
        </button>
      </form>

      {reassignRequests.length > 0 && (
        <>
          <h4>Your requests</h4>
          <table>
            <thead>
              <tr>
                <th>Doctor</th>
                <th>Disease</th>
                <th>Status</th>
                <th>Reason</th>
                <th>Admin Note</th>
                <th>Requested At</th>
              </tr>
            </thead>
            <tbody>
              {reassignRequests.map((r) => (
                <tr key={r.id}>
                  <td>{r.doctor_name || `ID: ${r.doctor_id}`}</td>
                  <td>{DISEASES[r.disease]?.label || r.disease}</td>
                  <td>{r.status}</td>
                  <td>{r.reason || "—"}</td>
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
