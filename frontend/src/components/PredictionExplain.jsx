import { useState } from "react";
import { apiFetch, downloadFile } from "../api/client.js";

// Small "Why?" toggle that fetches a SHAP feature-contribution breakdown
// for one specific prediction and shows it as simple bars - red pushed
// the result toward higher risk, green pushed it toward lower risk.
// Used on both the doctor's patient view and the patient's own
// dashboard/history, since the backend allows either to see it.
//
// Also carries the "Download PDF" button for the same prediction - not
// its own component, since it always shows up in exactly the same
// places as this one and shares the same predictionId prop.
export default function PredictionExplain({ predictionId, explainable = true }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  async function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (data || loading) return;
    setLoading(true);
    setError("");
    try {
      const res = await apiFetch(`/predictions/${predictionId}/explain`);
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDownload() {
    setDownloading(true);
    setDownloadError("");
    try {
      await downloadFile(
        `/predictions/${predictionId}/report`,
        `prediction-${predictionId}-report.pdf`
      );
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setDownloading(false);
    }
  }

  const downloadButton = (
    <button type="button" className="link-button" onClick={handleDownload} disabled={downloading}>
      {downloading ? "Preparing PDF..." : "Download PDF"}
    </button>
  );

  if (!explainable) {
    return (
      <span>
        <span className="hint">Not explainable (made before this feature)</span>{" "}
        {downloadButton}
        {downloadError && <p className="error">{downloadError}</p>}
      </span>
    );
  }

  const maxAbs = data
    ? Math.max(...data.contributions.map((c) => Math.abs(c.contribution)), 0.0001)
    : 1;

  return (
    <div>
      <button type="button" className="link-button" onClick={toggle}>
        {open ? "Hide reasoning" : "Why?"}
      </button>{" "}
      {downloadButton}
      {downloadError && <p className="error">{downloadError}</p>}
      {open && (
        <div className="card" style={{ marginTop: "0.5rem" }}>
          {loading && <p>Loading explanation...</p>}
          {error && <p className="error">{error}</p>}
          {data && (
            <>
              <p className="hint">
                What pushed this prediction toward {data.risk_level} the most:
              </p>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {data.contributions.slice(0, 8).map((c) => (
                  <li key={c.feature} style={{ marginBottom: "0.4rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.9em" }}>
                      <span>
                        {c.feature} ({c.value})
                      </span>
                      <span>
                        {c.contribution > 0 ? "+" : ""}
                        {c.contribution}
                      </span>
                    </div>
                    <div style={{ background: "#eee", height: "6px", borderRadius: "3px" }}>
                      <div
                        style={{
                          width: `${(Math.abs(c.contribution) / maxAbs) * 100}%`,
                          height: "100%",
                          borderRadius: "3px",
                          background: c.contribution > 0 ? "#d9534f" : "#5cb85c",
                        }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="hint">
                Red = pushed toward higher risk, green = pushed toward lower risk.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
