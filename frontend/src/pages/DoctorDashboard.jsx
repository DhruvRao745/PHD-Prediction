import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { DISEASES } from "../config/diseaseFields.js";
import Greeting from "../components/Greeting.jsx";
import Avatar from "../components/Avatar.jsx";
import EmptyState from "../components/EmptyState.jsx";
import RiskTrend from "../components/RiskTrend.jsx";

export default function DoctorDashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [patients, setPatients] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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

  if (loading) return <div className="page">Loading...</div>;

  const highRiskCount = patients.filter((p) => {
    const latest = p.predictions[p.predictions.length - 1];
    return latest?.risk === "High Risk";
  }).length;

  const summary =
    patients.length === 0
      ? "You don't have any patients assigned yet."
      : highRiskCount > 0
      ? `${highRiskCount} of your ${patients.length} assigned patient${patients.length === 1 ? "" : "s"} came back High Risk on their latest prediction.`
      : `All ${patients.length} of your assigned patients are currently Low Risk on their latest prediction.`;

  return (
    <div className="page">
      <Greeting name={profile?.name || user?.username} summary={summary} />

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

      {/* Assigning patients is admin-only now - see AdminDashboard.
          A patient can appear more than once here if you're assigned to
          them for more than one disease - each row links to that specific
          disease's detail page, not the patient's full cross-disease history. */}
      <h3>Your patients</h3>
      {patients.length === 0 && (
        <EmptyState
          title="No patients assigned yet"
          hint="Once admin assigns a patient to you for a specific disease, they'll show up here."
        />
      )}
      {patients.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Age</th>
              <th>Disease</th>
              <th>Latest risk</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {patients.map((p) => {
              const latest = p.predictions[p.predictions.length - 1];
              return (
                <tr key={`${p.patient_id}-${p.assigned_for}`}>
                  <td>
                    <div className="person-row">
                      <Avatar name={p.patient_name} size={28} />
                      <span>{p.patient_name}</span>
                    </div>
                  </td>
                  <td>{p.age ?? "—"}</td>
                  <td>{DISEASES[p.assigned_for]?.label || p.assigned_for}</td>
                  <td>
                    {latest ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                        <span className={`status-chip ${latest.risk === "High Risk" ? "danger" : "success"}`}>
                          {latest.risk}
                        </span>
                        <RiskTrend predictions={p.predictions} />
                      </div>
                    ) : (
                      <span className="hint">No data</span>
                    )}
                  </td>
                  <td>
                    <Link className="link-button" to={`/doctor/patient/${p.patient_id}?disease=${p.assigned_for}`}>
                      View details
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
