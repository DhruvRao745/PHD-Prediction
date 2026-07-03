import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";

// NOTE: same as /profile/patient - /profile/doctor takes query params,
// not a JSON body (FastAPI treats plain str args without a Pydantic
// model as query params).
export default function DoctorProfileForm() {
  const [name, setName] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [hospital, setHospital] = useState("");
  const [licenseNo, setLicenseNo] = useState("");
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
        specialization,
        hospital,
        license_no: licenseNo,
      });
      await apiFetch(`/profile/doctor?${params.toString()}`, {
        method: "POST",
      });
      setSuccess("Profile saved.");
      setTimeout(() => navigate("/doctor"), 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <p>
        <Link to="/doctor">&larr; Back to dashboard</Link>
      </p>
      <h2>Doctor Profile</h2>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Specialization
          <input
            value={specialization}
            onChange={(e) => setSpecialization(e.target.value)}
            required
          />
        </label>
        <label>
          Hospital
          <input value={hospital} onChange={(e) => setHospital(e.target.value)} required />
        </label>
        <label>
          License Number
          <input value={licenseNo} onChange={(e) => setLicenseNo(e.target.value)} required />
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
