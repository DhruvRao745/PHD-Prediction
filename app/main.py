from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import sys
from pathlib import Path

from streamlit import user
from app.registry.model_registry import MODEL_REGISTRY
from app.auth.routes import router as auth_router
from app.auth.security import get_current_user
from app.database import SessionLocal
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from app.deps import get_db
from app.services.prediction_service import save_prediction
from sqlalchemy.orm import Session
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_patient import DoctorPatient
from app.models.prediction import Prediction

# Ensure project root is on sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app.core.predictor import predict
except ModuleNotFoundError:
    from core.predictor import predict

app = FastAPI()
app.include_router(auth_router)


class PredictRequest(BaseModel):
    disease: str
    data: dict

@app.get("/")
def root():
    return {"message": "Welcome to the Multiple Disease Prediction API."}

# ------------------ PREDICT ------------------
@app.post("/predict")
def predict_api(
    request: PredictRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = predict(request.disease, request.data)

    risk = result["prediction"]["risk"]
    confidence = result["prediction"]["confidence"]

    save_prediction(
        db=db,
        patient_id=user["id"],
        disease=request.disease,
        risk_level=risk,
        probability=confidence,
        input_method="form",
        model_version="v1.0"
    )

    return result


# ------------------ HISTORY ------------------
@app.get("/history")
def get_history(
    disease: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Prediction).filter(
        Prediction.patient_id == user["id"]
    )

    if disease:
        query = query.filter(Prediction.disease == disease)

    return query.all()


# ------------------ PATIENT DASHBOARD ------------------
@app.get("/dashboard/patient")
def patient_dashboard(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Access denied")

    patient = db.query(PatientProfile).filter(
        PatientProfile.patient_id == user["id"]
    ).first()

    if not patient:
        raise HTTPException(404, "Patient profile not found")

    predictions = db.query(Prediction).filter(
        Prediction.patient_id == patient.patient_id
    ).all()

    return {
        "patient_profile": patient,
        "predictions": predictions
    }


# ------------------ DOCTOR DASHBOARD ------------------
@app.get("/dashboard/doctor")
def doctor_dashboard(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "doctor":
        raise HTTPException(403, "Access denied")

    doctor = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == user["id"]
    ).first()

    if not doctor:
        raise HTTPException(404, "Doctor profile not found")

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor.doctor_id   # ✅ FIXED
    ).all()

    patients_data = []

    for rel in relations:
        patient = db.query(PatientProfile).filter(
            PatientProfile.patient_id == rel.patient_id
        ).first()

        if not patient:
            continue

        predictions = db.query(Prediction).filter(
            Prediction.patient_id == patient.patient_id   # ✅ FIXED
        ).all()

        patients_data.append({
            "patient_id": patient.patient_id,
            "patient_name": patient.name,
            "age": patient.age,
            "predictions": [{
                "disease": p.disease,
                "risk": p.risk_level,
                "confidence": p.probability
            }
                for p in predictions
            ]
        })

    return {
        "doctor_profile": doctor,
        "patients": patients_data
    }


# ------------------ ASSIGN PATIENT ------------------
@app.post("/doctor/assign-patient")
def assign_patient(
    patient_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "doctor":
        raise HTTPException(403, "Only doctors allowed")

    doctor = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == user["id"]
    ).first()

    if not doctor:
        raise HTTPException(404, "Doctor profile not found")

    patient = db.query(PatientProfile).filter(
        PatientProfile.patient_id == patient_id
    ).first()

    if not patient:
        raise HTTPException(404, "Patient not found")

    existing = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor.doctor_id,
        DoctorPatient.patient_id == patient_id
    ).first()

    if existing:
        return {"message": "Patient already assigned"}

    relation = DoctorPatient(
        doctor_id=doctor.doctor_id,
        patient_id=patient_id
    )

    db.add(relation)
    db.commit()

    return {"message": "Patient assigned successfully"}

# --------- Patient Profile API ---------
@app.post("/profile/patient")
def create_patient_profile(
    name: str,
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    print("User from token:", user)  # 🔥 DEBUGGING LINE 
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients allowed")

    existing = db.query(PatientProfile).filter(
        PatientProfile.patient_id == user["id"]
    ).first()

    if existing:
        return {"message": "Profile already exists"}

    profile = PatientProfile(
        patient_id=user["id"],
        name=name,
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg
    )

    db.add(profile)
    db.commit()

    return {"message": "Patient profile created"}
   

# --------- Doctor Profile API ---------
@app.post("/profile/doctor")
def create_doctor_profile(
    name: str,
    specialization: str,
    hospital: str,
    license_no: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "doctor":
        raise HTTPException(403, "Only doctors allowed")

    existing = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == user["id"]
    ).first()

    if existing:
        return {"message": "Profile already exists"}

    profile = DoctorProfile(
        doctor_id=user["id"],
        name=name,
        specialization=specialization,
        hospital=hospital,
        license_no=license_no
    )

    db.add(profile)
    db.commit()

    return {"message": "Doctor profile created"}