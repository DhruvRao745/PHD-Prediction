import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { apiFetch } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import PredictionForm from "../components/PredictionForm.jsx";
import { DISEASES } from "../config/diseaseFields.js";

export default function Predict() {
  const { disease } = useParams();
  const config = DISEASES[disease];
  const { user } = useAuth();
  const isPatient = user?.role === "patient";
  const dashboardPath = user?.role === "doctor" ? "/doctor" : "/patient";

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      // Only patients have a PatientProfile (age/gender) to auto-fill
      // from. Doctors predicting on themselves just fill fields manually.
      if (!isPatient) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const res = await apiFetch("/dashboard/patient");
        setProfile(res.data.patient_profile);
      } catch {
        setProfile(null);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isPatient]);

  if (!config) {
    return (
      <div className="page">
        <p>Unknown disease: {disease}</p>
        <Link to={dashboardPath}>Back to dashboard</Link>
      </div>
    );
  }

  if (loading) {
    return <div className="page">Loading...</div>;
  }

  const profileIncomplete = isPatient && (!profile || profile.age == null || !profile.gender);

  return (
    <div className="page">
      <p>
        <Link to={dashboardPath}>&larr; Back to dashboard</Link>
      </p>
      <h2>{config.label} Risk Prediction</h2>

      {profileIncomplete && (
        <p className="note">
          Fill out your <Link to="/profile/patient">patient profile</Link> (age
          and gender) first - the form uses it to auto-fill and lock fields
          like age, sex, and pregnancies so they can't be entered
          inconsistently.
        </p>
      )}

      <PredictionForm key={disease} diseaseKey={disease} patientProfile={profile} />
    </div>
  );
}
