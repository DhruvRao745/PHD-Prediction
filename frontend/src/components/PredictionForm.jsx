import { useState } from "react";
import { apiFetch } from "../api/client.js";
import { DISEASES } from "../config/diseaseFields.js";
import { parseInput } from "../utils/parseInput.js";

// Figures out which fields should be derived from the patient's own
// profile instead of typed/pasted in - age should always match their
// real age, heart's "sex" should match their real gender, and a male
// patient can't have a non-zero pregnancy count.
function getLockedFields(diseaseKey, fields, profile) {
  const locked = {};
  if (!profile) return locked;

  const gender = profile.gender ? String(profile.gender).trim().toLowerCase() : null;

  fields.forEach((field) => {
    const norm = field.name.toLowerCase();

    if (norm === "age" && profile.age != null) {
      locked[field.name] = profile.age;
    }

    // Standard UCI heart dataset convention: 1 = male, 0 = female.
    if (diseaseKey === "heart" && norm === "sex" && (gender === "male" || gender === "female")) {
      locked[field.name] = gender === "male" ? 1 : 0;
    }

    if (diseaseKey === "diabetes" && field.name === "Pregnancies" && gender === "male") {
      locked[field.name] = 0;
    }
  });

  return locked;
}

// Renders a prediction form for any of the 4 diseases from the shared
// config, submits to POST /predict, and shows the risk/confidence
// result or validation errors returned by the backend.
export default function PredictionForm({ diseaseKey, patientProfile }) {
  const disease = DISEASES[diseaseKey];
  const lockedFields = getLockedFields(diseaseKey, disease.fields, patientProfile);

  const initialState = {};
  disease.fields.forEach((field) => {
    if (field.name in lockedFields) {
      initialState[field.name] = lockedFields[field.name];
    } else if (field.type === "select") {
      const firstOption = field.options[0];
      initialState[field.name] =
        typeof firstOption === "object" ? firstOption.value : firstOption;
    } else {
      initialState[field.name] = "";
    }
  });

  const [values, setValues] = useState(initialState);
  const [result, setResult] = useState(null);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [bulkText, setBulkText] = useState("");
  const [bulkMessage, setBulkMessage] = useState("");

  function handleChange(field, rawValue) {
    if (field.name in lockedFields) return;
    setValues((prev) => ({ ...prev, [field.name]: rawValue }));
  }

  function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setBulkText(String(reader.result));
    reader.readAsText(file);
  }

  function handleBulkFill() {
    try {
      const parsed = parseInput(bulkText, disease.fields);
      // Profile-derived fields (age, sex, pregnancies) stay locked even
      // if the pasted/uploaded data contains different values for them.
      const filtered = Object.fromEntries(
        Object.entries(parsed).filter(([name]) => !(name in lockedFields))
      );
      const matchedCount = Object.keys(filtered).length;
      if (matchedCount === 0) {
        setBulkMessage("Couldn't match any editable fields - check the format below.");
        return;
      }
      setValues((prev) => ({ ...prev, ...filtered }));
      setBulkMessage(`Filled ${matchedCount} of ${disease.fields.length} fields.`);
    } catch (err) {
      setBulkMessage(`Couldn't parse input: ${err.message}`);
    }
  }

  function buildPayload() {
    const data = {};
    disease.fields.forEach((field) => {
      const raw = values[field.name];
      if (field.type === "select") {
        const firstOption = field.options[0];
        data[field.name] =
          typeof firstOption === "object" ? Number(raw) : raw;
      } else {
        data[field.name] = raw === "" ? null : Number(raw);
      }
    });
    return data;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrors([]);
    setResult(null);
    setLoading(true);
    try {
      const res = await apiFetch("/predict", {
        method: "POST",
        body: { disease: diseaseKey, data: buildPayload() },
      });
      setResult(res.data);
      if (res.message) {
        setResult({ ...res.data, note: res.message });
      }
    } catch (err) {
      if (Array.isArray(err.data?.detail?.details)) {
        setErrors(err.data.detail.details);
      } else {
        setErrors([err.message]);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="bulk-fill">
        <h4>Quick fill from data</h4>
        <p className="hint">
          Paste JSON (<code>{'{"Age": 31, ...}'}</code>), a CSV row (with or
          without a header), "field: value" lines, or upload a .csv/.txt/.json
          file. Fields auto-filled from your profile (age, sex, pregnancies)
          stay locked.
        </p>
        <input type="file" accept=".csv,.txt,.json" onChange={handleFileUpload} />
        <textarea
          rows={3}
          placeholder="Paste data here..."
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
        />
        <button type="button" onClick={handleBulkFill}>
          Fill form
        </button>
        {bulkMessage && <p className="note">{bulkMessage}</p>}
      </div>

      <form onSubmit={handleSubmit} className="form predict-form">
        {disease.fields.map((field) => {
          const isLocked = field.name in lockedFields;
          return (
            <label key={field.name}>
              {field.label}
              {isLocked && <span className="locked-hint"> (from your profile)</span>}
              {field.type === "select" ? (
                <select
                  value={values[field.name]}
                  onChange={(e) => handleChange(field, e.target.value)}
                  disabled={isLocked}
                >
                  {field.options.map((opt) => {
                    const value = typeof opt === "object" ? opt.value : opt;
                    const label = typeof opt === "object" ? opt.label : opt;
                    return (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              ) : (
                <input
                  type="number"
                  min={field.min}
                  max={field.max}
                  step="any"
                  value={values[field.name]}
                  onChange={(e) => handleChange(field, e.target.value)}
                  disabled={isLocked}
                  required
                />
              )}
            </label>
          );
        })}
        <button type="submit" disabled={loading}>
          {loading ? "Predicting..." : "Predict"}
        </button>
      </form>

      {errors.length > 0 && (
        <div className="error">
          <p>Please fix the following:</p>
          <ul>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <div className={`result ${result.risk === "High Risk" ? "high-risk" : "low-risk"}`}>
          <h3>{result.risk}</h3>
          <p>Confidence: {result.confidence}</p>
          {result.note && <p className="note">{result.note}</p>}
        </div>
      )}
    </div>
  );
}
