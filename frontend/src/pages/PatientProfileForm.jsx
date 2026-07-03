import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";

// NOTE: /profile/patient takes these as query params, not a JSON body
// (the FastAPI route declares them as plain str/int/float args, which
// FastAPI treats as query params since there's no Pydantic model).
export default function PatientProfileForm() {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("male");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const params = new URLSearchParams({
        name,
        age: String(age),
        gender,
        height_cm: String(heightCm),
        weight_kg: String(weightKg),
      });
      await apiFetch(`/profile/patient?${params.toString()}`, {
        method: "POST",
      });
      setSuccess("Profile saved.");
      setTimeout(() => navigate("/patient"), 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <p>
        <Link to="/patient">&larr; Back to dashboard</Link>
      </p>
      <h2>Patient Profile</h2>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Age
          <input type="number" min="0" max="130" value={age} onChange={(e) => setAge(e.target.value)} required />
        </label>
        <label>
          Gender
          <select value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label>
          Height (cm)
          <input type="number" min="0" step="0.1" value={heightCm} onChange={(e) => setHeightCm(e.target.value)} required />
        </label>
        <label>
          Weight (kg)
          <input type="number" min="0" step="0.1" value={weightKg} onChange={(e) => setWeightKg(e.target.value)} required />
        </label>
        {error && <p className="error">{error}</p>}
        {success && <p className="success">{success}</p>}
        <button type="submit" disabled={loading}>
          {loading ? "Saving..." : "Save Profile"}
        </button>
      </form>
    </div>
  );
}
