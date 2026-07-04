import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { DISEASES } from "../config/diseaseFields.js";
import { getDashboardPath } from "../utils/roles.js";

export default function History() {
  const { user } = useAuth();
  const dashboardPath = getDashboardPath(user?.role);
  const [disease, setDisease] = useState("");
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");
  const [deleteError, setDeleteError] = useState("");
  const [loading, setLoading] = useState(true);

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

  useEffect(() => {
    load();
  }, [disease]);

  async function handleDelete(id) {
    setDeleteError("");
    try {
      await apiFetch(`/predictions/${id}`, { method: "DELETE" });
      setRecords((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setDeleteError(err.message);
    }
  }

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
      {deleteError && <p className="error">{deleteError}</p>}

      {!loading && !error && records.length === 0 && <p>No predictions yet.</p>}

      {!loading && records.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Disease</th>
              <th>Risk</th>
              <th>Confidence</th>
              <th>Date</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id}>
                <td>{DISEASES[r.disease]?.label || r.disease}</td>
                <td>{r.risk_level}</td>
                <td>{r.probability}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>
                  <button type="button" className="link-button" onClick={() => handleDelete(r.id)}>
                    Delete
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
