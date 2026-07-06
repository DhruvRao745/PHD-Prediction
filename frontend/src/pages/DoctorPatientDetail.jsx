import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";
import Avatar from "../components/Avatar.jsx";
import PredictionExplain from "../components/PredictionExplain.jsx";
import RiskTrend from "../components/RiskTrend.jsx";

// Dedicated full-page view for one patient, scoped to the one disease a
// doctor is assigned for - separate from the summary list on the doctor
// dashboard, so a patient with real history gets more room than a card
// squeezed onto a list can give it.
export default function DoctorPatientDetail() {
  const { patientId } = useParams();
  const [searchParams] = useSearchParams();
  const disease = searchParams.get("disease");

  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await apiFetch(`/doctor/patients/${patientId}?disease=${encodeURIComponent(disease)}`);
        setData(res);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    if (patientId && disease) load();
  }, [patientId, disease]);

  if (loading) return <div className="page">Loading...</div>;

  if (error) {
    return (
      <div className="page">
        <p>
          <Link to="/doctor">&larr; Back to dashboard</Link>
        </p>
        <p className="error">{error}</p>
      </div>
    );
  }

  const latest = data.predictions[data.predictions.length - 1];

  return (
    <div className="page" style={{ maxWidth: 720 }}>
      <p>
        <Link to="/doctor">&larr; Back to dashboard</Link>
      </p>

      <div className="person-row" style={{ marginBottom: "1rem" }}>
        <Avatar name={data.patient_name} size={44} />
        <div>
          <h2 style={{ margin: 0 }}>{data.patient_name}</h2>
          <p className="hint" style={{ margin: 0 }}>
            Age {data.age ?? "—"} · {data.gender ?? "—"} · assigned for{" "}
            {DISEASES[data.disease]?.label || data.disease} since{" "}
            {new Date(data.assigned_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {latest && (
        <div className="metrics-row">
          <div className={`metric-card${latest.risk === "High Risk" ? " warning" : ""}`}>
            <p className="metric-label">Latest risk</p>
            <p className="metric-value">{latest.risk}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Latest confidence</p>
            <p className="metric-value">{latest.confidence}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">Total predictions</p>
            <p className="metric-value">{data.predictions.length}</p>
          </div>
        </div>
      )}

      {data.predictions.length > 1 && (
        <p style={{ marginTop: "-0.75rem", marginBottom: "1rem" }}>
          <RiskTrend predictions={data.predictions} /> since last prediction
        </p>
      )}

      {data.predictions.length === 0 && <p>No predictions recorded yet.</p>}

      {data.predictions.length > 1 && (
        <div className="card" style={{ height: 240 }}>
          <ResponsiveContainer>
            <LineChart
              data={data.predictions.map((pred) => ({
                time: new Date(pred.time).toLocaleDateString(),
                confidence: pred.confidence,
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis domain={[0, 1]} />
              <Tooltip />
              <Line type="monotone" dataKey="confidence" stroke="#2563eb" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {data.predictions.length > 0 && (
        <>
          <h3>Prediction history</h3>
          <table>
            <thead>
              <tr>
                <th>Risk</th>
                <th>Confidence</th>
                <th>Date</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {[...data.predictions].reverse().map((pred) => (
                <tr key={pred.id}>
                  <td>
                    <span className={`status-chip ${pred.risk === "High Risk" ? "danger" : "success"}`}>
                      {pred.risk}
                    </span>
                  </td>
                  <td>{pred.confidence}</td>
                  <td>{new Date(pred.time).toLocaleString()}</td>
                  <td>
                    <PredictionExplain predictionId={pred.id} explainable={pred.explainable} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
