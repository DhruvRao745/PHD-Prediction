import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { DISEASES } from "../config/diseaseFields.js";

export default function History() {
  const { user } = useAuth();
  const dashboardPath = user?.role === "doctor" ? "/doctor" : "/patient";
  const [disease, setDisease] = useState("");
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const query = disease ? `?disease=${encodeURIComponent(disease)}` : "";
        const data = await apiFetch(`/history${query}`);
        setRecords(Array.isArray(data) ? data : []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [disease]);

  return (
    <div className="page">
      <p>
        <Link to={dashboardPath}>&larr; Back to dashboard</Link>
      </p>
      <h2>Prediction History</h2>

      <label>
        Filter by disease
        <select value={disease} onChange={(e) => setDisease(e.target.value)}>
          <option value="">All</option>
          {Object.entries(DISEASES).map(([key, d]) => (
            <option key={key} value={key}>
              {d.label}
            </option>
          ))}
        </select>
      </label>

      {loading && <p>Loading...</p>}
      {error && <p className="error">{error}</p>}

      {!loading && !error && records.length === 0 && <p>No predictions yet.</p>}

      {!loading && records.length > 0 && (
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
            {records.map((r) => (
              <tr key={r.id}>
                <td>{DISEASES[r.disease]?.label || r.disease}</td>
                <td>{r.risk_level}</td>
                <td>{r.probability}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
