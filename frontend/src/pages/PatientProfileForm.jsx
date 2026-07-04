import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";

// name is intentionally NOT part of the direct-edit form below - patients
// can't rename themselves, they have to submit a request (see the
// "Request name change" section) that admin approves or denies.
export default function PatientProfileForm() {
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("male");
  const [heightCm, setHeightCm] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const [pendingNameRequest, setPendingNameRequest] = useState(null);
  const [nameRequestHistory, setNameRequestHistory] = useState([]);
  const [newName, setNewName] = useState("");
  const [nameReason, setNameReason] = useState("");
  const [requestingName, setRequestingName] = useState(false);
  const [nameRequestMsg, setNameRequestMsg] = useState("");
  const [nameRequestErr, setNameRequestErr] = useState("");

  async function load() {
    setLoadingProfile(true);
    setError("");
    try {
      const [profile, requests] = await Promise.all([
        apiFetch("/profile/patient"),
        apiFetch("/profile/change-requests"),
      ]);
      setName(profile.name || "");
      setAge(profile.age ?? "");
      setGender(profile.gender || "male");
      setHeightCm(profile.height_cm ?? "");
      setWeightKg(profile.weight_kg ?? "");

      const nameRequests = (requests || []).filter((r) => r.field === "name");
      setNameRequestHistory(nameRequests);
      setPendingNameRequest(nameRequests.find((r) => r.status === "pending") || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingProfile(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      await apiFetch("/profile/patient", {
        method: "PATCH",
        body: {
          age: age === "" ? null : Number(age),
          gender,
          height_cm: heightCm === "" ? null : Number(heightCm),
          weight_kg: weightKg === "" ? null : Number(weightKg),
        },
      });
      setSuccess("Profile saved.");
      setTimeout(() => navigate("/patient"), 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRequestNameChange(e) {
    e.preventDefault();
    setNameRequestMsg("");
    setNameRequestErr("");
    setRequestingName(true);
    try {
      const res = await apiFetch("/profile/change-request", {
        method: "POST",
        body: { field: "name", requested_value: newName, reason: nameReason || null },
      });
      setNameRequestMsg(res.message);
      setNewName("");
      setNameReason("");
      await load();
    } catch (err) {
      setNameRequestErr(err.message);
    } finally {
      setRequestingName(false);
    }
  }

  if (loadingProfile) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <p>
        <Link to="/patient">&larr; Back to dashboard</Link>
      </p>
      <h2>Patient Profile</h2>

      <div className="card">
        <p>
          <strong>Name:</strong> {name}
        </p>
        <p className="hint">
          Name changes need admin approval - use the form below to request one.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="form">
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
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save Profile"}
        </button>
      </form>

      <h3>Request a name change</h3>
      {pendingNameRequest ? (
        <p className="hint">
          You already have a pending request to change your name to "
          {pendingNameRequest.requested_value}" - waiting on admin.
        </p>
      ) : (
        <form onSubmit={handleRequestNameChange} className="form">
          <label>
            New name
            <input value={newName} onChange={(e) => setNewName(e.target.value)} required />
          </label>
          <label>
            Reason (optional)
            <input value={nameReason} onChange={(e) => setNameReason(e.target.value)} />
          </label>
          {nameRequestErr && <p className="error">{nameRequestErr}</p>}
          {nameRequestMsg && <p className="success">{nameRequestMsg}</p>}
          <button type="submit" disabled={requestingName}>
            {requestingName ? "Submitting..." : "Request Name Change"}
          </button>
        </form>
      )}

      {nameRequestHistory.length > 0 && (
        <>
          <h4>Your name change requests</h4>
          <table>
            <thead>
              <tr>
                <th>Requested Name</th>
                <th>Status</th>
                <th>Admin Note</th>
                <th>Requested At</th>
              </tr>
            </thead>
            <tbody>
              {nameRequestHistory.map((r) => (
                <tr key={r.id}>
                  <td>{r.requested_value}</td>
                  <td>{r.status}</td>
                  <td>{r.admin_note || "—"}</td>
                  <td>{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
