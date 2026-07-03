import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";

export default function PatientDashboard() {
  const [profile, setProfile] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await apiFetch("/dashboard/patient");
        setProfile(res.data.patient_profile);
        setPredictions(res.data.predictions || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

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

      <h3>Run a prediction</h3>
      <div className="button-row">
        {Object.entries(DISEASES).map(([key, d]) => (
          <Link key={key} className="button-link" to={`/predict/${key}`}>
            {d.label}
          </Link>
        ))}
      </div>

      <h3>Recent predictions</h3>
      {predictions.length === 0 && <p>No predictions yet.</p>}
      {predictions.length > 0 && (
        <ul>
          {predictions.map((p) => (
            <li key={p.id}>
              {DISEASES[p.disease]?.label || p.disease}: {p.risk_level} (
              {p.probability}) — {new Date(p.created_at).toLocaleString()}
            </li>
          ))}
        </ul>
      )}
      <p>
        <Link to="/history">View full history</Link>
      </p>
    </div>
  );
}
