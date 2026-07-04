from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path
from app.registry.model_registry import MODEL_REGISTRY
from app.auth.routes import router as auth_router
from app.admin.routes import router as admin_router
from app.auth.security import get_current_user
from app.database import SessionLocal
from datetime import datetime
from app.deps import get_db
from app.services.prediction_service import save_prediction
from sqlalchemy.orm import Session
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_patient import DoctorPatient
from app.models.prediction import Prediction
from app.models.reassignment_request import ReassignmentRequest
from datetime import datetime, timedelta
from sqlalchemy import and_

# Ensure project root is on sys.path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app.core.predictor import predict
except ModuleNotFoundError:
    from core.predictor import predict

app = FastAPI()

# Allow the React (Vite) dev server to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)


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
# ------------- inside predict_api --------------
    result = predict(request.disease, request.data)

    if "error" in result:
        raise HTTPException(
            status_code=400,
            detail=result,
        )
    risk = result["prediction"]["risk"]
    confidence = result["prediction"]["confidence"]
    
    
    # Time-based duplicate check
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Check similar prediction (not exact float match)
    existing = db.query(Prediction).filter(
        Prediction.patient_id == user["id"],
        Prediction.disease == request.disease,
        Prediction.created_at >= one_hour_ago,
        and_(
            Prediction.probability >= confidence - 0.01,  # Allow small margin
            Prediction.probability <= confidence + 0.01
        )
    ).first()
    
    # Skip if duplicate
    if existing:
        return {
            "status": "success",
            "message": "Duplicate prediction skipped",
            "data": result["prediction"]
        }
    
    # Save only if not duplicate
    save_prediction(
        db=db,
        patient_id=user["id"],
        disease=request.disease,
        risk_level=risk,
        probability=confidence,
        input_method="form",
        model_version="v1.0"
    )

    return {
        "status": "success",
        "data": result["prediction"]
        }


# ------------------ HISTORY ------------------
@app.get("/history")
def get_history(
    disease: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    Predictions = db.query(Prediction).filter(
        Prediction.patient_id == user["id"],
        Prediction.deleted_at.is_(None)
    ).order_by(Prediction.created_at.desc()).limit(5).all()

    if disease:
        Predictions = db.query(Prediction).filter(
            Prediction.patient_id == user["id"],
            Prediction.disease == disease,
            Prediction.deleted_at.is_(None)
        ).order_by(Prediction.created_at.desc()).limit(5).all()

    return Predictions


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
        Prediction.patient_id == patient.patient_id,
        Prediction.deleted_at.is_(None)
    ).order_by(Prediction.created_at.desc()).limit(5).all()

    return {
        "status": "success",
        "data" : {
            "patient_profile": patient,
            "predictions": predictions
        }
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

    # Only active (non-unassigned) links - once admin unassigns a doctor
    # from a patient, this soft-delete filter is what fully revokes the
    # doctor's access to that patient's data, past and future.
    relations = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor.doctor_id,
        DoctorPatient.deleted_at.is_(None)
    ).all()

    patients_data = []

    for rel in relations:
        patient = db.query(PatientProfile).filter(
            PatientProfile.patient_id == rel.patient_id
        ).first()

        if not patient:
            continue

        predictions = db.query(Prediction).filter(
            Prediction.patient_id == patient.patient_id,
            Prediction.deleted_at.is_(None)
        ).all()

        patients_data.append({
            "patient_id": patient.patient_id,
            "patient_name": patient.name,
            "age": patient.age,
            "predictions": [{
                "disease": p.disease,
                "risk": p.risk_level,
                "confidence": p.probability,
                "time" : p.created_at
            }
                for p in predictions
            ]
        })

    return {
        "status": "success",
        "data": {
            "doctor_profile": doctor,
            "patients": patients_data
        }
    }


# ------------------ DELETE (SOFT) OWN PREDICTION ------------------
# Patients/doctors can remove their own predictions from their own view.
# Patients are blocked entirely if they have an active assigned doctor -
# only admin can remove that record in that case. Doctors can only ever
# delete their own self-run predictions (never a patient's).
@app.delete("/predictions/{prediction_id}")
def delete_own_prediction(
    prediction_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.patient_id == user["id"],
        Prediction.deleted_at.is_(None)
    ).first()

    if not prediction:
        raise HTTPException(404, "Prediction not found")

    if user["role"] == "patient":
        has_active_doctor = db.query(DoctorPatient).filter(
            DoctorPatient.patient_id == user["id"],
            DoctorPatient.deleted_at.is_(None)
        ).first()

        if has_active_doctor:
            raise HTTPException(
                403,
                "You have an assigned doctor - only admin can remove this record"
            )

    prediction.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "Prediction deleted"}


# ------------------ REQUEST DOCTOR REASSIGNMENT ------------------
# Patients can't unassign their own doctor directly - only admin can.
# This lets a patient flag "I want a different doctor" for admin to act on.
class ReassignmentRequestData(BaseModel):
    reason: str | None = None


@app.post("/reassignment-request")
def request_reassignment(
    data: ReassignmentRequestData,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients can request reassignment")

    existing_pending = db.query(ReassignmentRequest).filter(
        ReassignmentRequest.patient_id == user["id"],
        ReassignmentRequest.status == "pending"
    ).first()

    if existing_pending:
        raise HTTPException(400, "You already have a pending reassignment request")

    current_assignment = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == user["id"],
        DoctorPatient.deleted_at.is_(None)
    ).first()

    request_row = ReassignmentRequest(
        patient_id=user["id"],
        doctor_id=current_assignment.doctor_id if current_assignment else None,
        reason=data.reason
    )

    db.add(request_row)
    db.commit()

    return {"message": "Reassignment request submitted"}


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
        existing.name = name
        existing.age = age
        existing.gender = gender
        existing.height_cm = height_cm
        existing.weight_kg = weight_kg
        db.commit()
        return {"message": "Profile updated"}

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
        existing.name = name
        existing.specialization = specialization
        existing.hospital = hospital
        existing.license_no = license_no
        db.commit()
        return {"message": "Profile updated"}

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