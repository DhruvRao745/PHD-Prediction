import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";

export default function DoctorDashboard() {
  const [profile, setProfile] = useState(null);
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [assignId, setAssignId] = useState("");
  const [assignMessage, setAssignMessage] = useState("");
  const [assignError, setAssignError] = useState("");
  const [assigning, setAssigning] = useState(false);

  async function loadDashboard() {
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch("/dashboard/doctor");
      setProfile(res.data.doctor_profile);
      setPatients(res.data.patients || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  async function handleAssign(e) {
    e.preventDefault();
    setAssignMessage("");
    setAssignError("");
    setAssigning(true);
    try {
      const res = await apiFetch(`/doctor/assign-patient?patient_id=${encodeURIComponent(assignId)}`, {
        method: "POST",
      });
      setAssignMessage(res.message);
      setAssignId("");
      await loadDashboard();
    } catch (err) {
      setAssignError(err.message);
    } finally {
      setAssigning(false);
    }
  }

  if (loading) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <h2>Doctor Dashboard</h2>

      {error && <p className="error">{error}</p>}

      {profile && (
        <div className="card">
          <h3>{profile.name}</h3>
          <p>
            {profile.specialization ?? "—"} at {profile.hospital ?? "—"} | License:{" "}
            {profile.license_no ?? "—"}
          </p>
          <Link to="/profile/doctor">Edit profile</Link>
        </div>
      )}

      <h3>Check your own risk</h3>
      <div className="button-row">
        {Object.entries(DISEASES).map(([key, d]) => (
          <Link key={key} className="button-link" to={`/predict/${key}`}>
            {d.label}
          </Link>
        ))}
      </div>
      <p>
        <Link to="/history">View your prediction history</Link>
      </p>

      <h3>Assign a patient</h3>
      <p className="hint">
        Enter a patient's account ID (ask the patient for their ID - there's
        no patient search yet, this only takes a numeric ID).
      </p>
      <form onSubmit={handleAssign} className="form" style={{ flexDirection: "row", alignItems: "flex-end", gap: "0.5rem" }}>
        <label style={{ flex: 1 }}>
          Patient ID
          <input
            type="number"
            value={assignId}
            onChange={(e) => setAssignId(e.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={assigning}>
          {assigning ? "Assigning..." : "Assign"}
        </button>
      </form>
      {assignMessage && <p className="success">{assignMessage}</p>}
      {assignError && <p className="error">{assignError}</p>}

      <h3>Your patients</h3>
      {patients.length === 0 && <p>No patients assigned yet.</p>}
      {patients.map((p) => (
        <div className="card" key={p.patient_id}>
          <h4>
            {p.patient_name} (ID: {p.patient_id}), Age: {p.age ?? "—"}
          </h4>
          {p.predictions.length === 0 && <p>No predictions yet.</p>}
          {p.predictions.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>Disease</th>
                  <th>Risk</th>
                  <th>Confidence</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {p.predictions.map((pred, i) => (
                  <tr key={i}>
                    <td>{DISEASES[pred.disease]?.label || pred.disease}</td>
                    <td>{pred.risk}</td>
                    <td>{pred.confidence}</td>
                    <td>{new Date(pred.time).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ))}
    </div>
  );
}
