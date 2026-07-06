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
from app.models.profile_change_request import ProfileChangeRequest
from datetime import datetime, timedelta
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

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
        Prediction.account_id == user["id"],
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
        account_id=user["id"],
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
        Prediction.account_id == user["id"],
        Prediction.deleted_at.is_(None)
    ).order_by(Prediction.created_at.desc()).limit(5).all()

    if disease:
        Predictions = db.query(Prediction).filter(
            Prediction.account_id == user["id"],
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
        Prediction.account_id == patient.patient_id,
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

        # Scoped to the specific disease this assignment is for - a
        # doctor assigned only for "heart" doesn't see this patient's
        # kidney/diabetes/parkinsons predictions. If the same doctor is
        # separately assigned to this same patient for a second disease,
        # that's a second row in `relations`, so this patient will show
        # up again below as its own entry for that other disease.
        predictions = db.query(Prediction).filter(
            Prediction.account_id == patient.patient_id,
            Prediction.disease == rel.disease,
            Prediction.deleted_at.is_(None)
        ).all()

        patients_data.append({
            "patient_id": patient.patient_id,
            "patient_name": patient.name,
            "age": patient.age,
            "assigned_for": rel.disease,
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
        Prediction.account_id == user["id"],
        Prediction.deleted_at.is_(None)
    ).first()

    if not prediction:
        raise HTTPException(404, "Prediction not found")

    if user["role"] == "patient":
        # Scoped to THIS prediction's disease - a patient with a heart
        # doctor but no kidney doctor should still be free to delete
        # their own kidney predictions, since nobody's actually watching
        # those. Only blocked if a doctor is specifically assigned for
        # the disease this particular prediction is about.
        has_active_doctor_for_disease = db.query(DoctorPatient).filter(
            DoctorPatient.patient_id == user["id"],
            DoctorPatient.disease == prediction.disease,
            DoctorPatient.deleted_at.is_(None)
        ).first()

        if has_active_doctor_for_disease:
            raise HTTPException(
                403,
                "You have an assigned doctor for this disease - only admin can remove this record"
            )

    prediction.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "Prediction deleted"}


# ------------------ REQUEST DOCTOR REASSIGNMENT ------------------
# Patients can't unassign their own doctor directly - only admin can.
# This lets a patient flag "I want to be removed from this specific
# doctor, for this specific disease" for admin to act on. Both doctor_id
# and disease are required - doctor_patient is scoped per disease, so
# the same doctor could in theory be assigned to a patient for two
# different diseases, and doctor_id alone wouldn't say which one the
# patient means.
class ReassignmentRequestData(BaseModel):
    doctor_id: int
    disease: str
    reason: str | None = None


# So the frontend has something to populate the "which doctor" dropdown
# with when a patient submits a reassignment request. A doctor can
# appear more than once here if they're assigned for more than one
# disease - each entry is really "this doctor, for this disease".
@app.get("/my-doctors")
def my_doctors(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients can view their assigned doctors")

    relations = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == user["id"],
        DoctorPatient.deleted_at.is_(None)
    ).all()

    results = []
    for r in relations:
        doctor = db.query(DoctorProfile).filter(DoctorProfile.doctor_id == r.doctor_id).first()
        if doctor:
            results.append({
                "doctor_id": doctor.doctor_id,
                "name": doctor.name,
                "specialization": doctor.specialization,
                "hospital": doctor.hospital,
                "disease": r.disease,
            })
    return results


@app.post("/reassignment-request")
def request_reassignment(
    data: ReassignmentRequestData,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients can request reassignment")

    # Make sure this is actually one of the patient's current assignments
    # - otherwise a patient could name any doctor_id/disease combo, real
    # assignment or not.
    active_assignment = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == data.doctor_id,
        DoctorPatient.patient_id == user["id"],
        DoctorPatient.disease == data.disease,
        DoctorPatient.deleted_at.is_(None)
    ).first()

    if not active_assignment:
        raise HTTPException(400, "This doctor is not currently assigned to you for this disease")

    # Scoped to this specific (doctor, disease) now, not the patient
    # overall - a patient with two doctors should be able to request
    # reassignment away from one of them while keeping a separate
    # pending request open against the other.
    existing_pending = db.query(ReassignmentRequest).filter(
        ReassignmentRequest.patient_id == user["id"],
        ReassignmentRequest.doctor_id == data.doctor_id,
        ReassignmentRequest.disease == data.disease,
        ReassignmentRequest.status == "pending"
    ).first()

    if existing_pending:
        raise HTTPException(400, "You already have a pending request for this doctor/disease")

    request_row = ReassignmentRequest(
        patient_id=user["id"],
        doctor_id=data.doctor_id,
        disease=data.disease,
        reason=data.reason
    )

    db.add(request_row)
    db.commit()

    return {"message": "Reassignment request submitted"}


# So a patient can actually see the outcome of their own request instead
# of submitting it into a void - status plus admin_note if it was denied.
@app.get("/reassignment-requests")
def my_reassignment_requests(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients can view their reassignment requests")

    rows = db.query(ReassignmentRequest).filter(
        ReassignmentRequest.patient_id == user["id"]
    ).order_by(ReassignmentRequest.created_at.desc()).all()

    results = []
    for r in rows:
        doctor = db.query(DoctorProfile).filter(DoctorProfile.doctor_id == r.doctor_id).first()
        results.append({
            "id": r.id,
            "doctor_id": r.doctor_id,
            "doctor_name": doctor.name if doctor else None,
            "disease": r.disease,
            "reason": r.reason,
            "status": r.status,
            "admin_note": r.admin_note,
            "created_at": r.created_at,
            "resolved_at": r.resolved_at,
        })
    return results


# --------- Patient Profile API ---------
# `name` is NOT here - patients can't rename themselves directly, they
# have to submit a request via /profile/change-request for admin
# approval. Everything else (age/gender/height/weight) is their own
# self-reported data, so it's a direct partial update.
class PatientProfileUpdate(BaseModel):
    age: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None


@app.get("/profile/patient")
def get_patient_profile(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients allowed")

    profile = db.query(PatientProfile).filter(
        PatientProfile.patient_id == user["id"]
    ).first()

    if not profile:
        raise HTTPException(404, "Patient profile not found")

    return {
        "patient_id": profile.patient_id,
        "name": profile.name,
        "age": profile.age,
        "gender": profile.gender,
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "created_at": profile.created_at,
        "username": user["username"],
        "email": user["email"],
    }


@app.patch("/profile/patient")
def update_patient_profile(
    data: PatientProfileUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "patient":
        raise HTTPException(403, "Only patients allowed")

    profile = db.query(PatientProfile).filter(
        PatientProfile.patient_id == user["id"]
    ).first()

    if not profile:
        raise HTTPException(404, "Patient profile not found")

    # exclude_unset means only fields the client actually sent get
    # touched - this is the real fix for "it made me fill in everything
    # just to change one field".
    for field, value in data.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()

    return {"message": "Profile updated"}


# --------- Doctor Profile API ---------
# Only license_no lives here, and only until it's set once. name,
# specialization, and hospital all require admin approval via
# /profile/change-request. If license_no itself gets entered wrong,
# that's fixed only by admin directly (/admin/doctors/{id}/license) -
# a doctor can never touch it themselves once it's set.
class DoctorProfileUpdate(BaseModel):
    license_no: str | None = None


@app.get("/profile/doctor")
def get_doctor_profile(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "doctor":
        raise HTTPException(403, "Only doctors allowed")

    profile = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == user["id"]
    ).first()

    if not profile:
        raise HTTPException(404, "Doctor profile not found")

    return {
        "doctor_id": profile.doctor_id,
        "name": profile.name,
        "specialization": profile.specialization,
        "hospital": profile.hospital,
        "license_no": profile.license_no,
        "created_at": profile.created_at,
        "username": user["username"],
        "email": user["email"],
    }


@app.patch("/profile/doctor")
def update_doctor_profile(
    data: DoctorProfileUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] != "doctor":
        raise HTTPException(403, "Only doctors allowed")

    profile = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == user["id"]
    ).first()

    if not profile:
        raise HTTPException(404, "Doctor profile not found")

    if data.license_no is not None:
        if profile.license_no:
            raise HTTPException(400, "License number is already set - contact admin to correct it")

        # Check against every OTHER doctor's license_no before touching the
        # DB - without this, two doctors submitting the same number both
        # pass this function's own logic and only the second commit fails,
        # as a raw unhandled IntegrityError (500) instead of a clean 400.
        duplicate = db.query(DoctorProfile).filter(
            DoctorProfile.license_no == data.license_no,
            DoctorProfile.doctor_id != user["id"]
        ).first()
        if duplicate:
            raise HTTPException(400, "This license number is already registered to another doctor")

        profile.license_no = data.license_no
        try:
            db.commit()
        except IntegrityError:
            # Belt-and-suspenders: covers the rare race where two requests
            # pass the check above at almost the same instant. The DB's
            # unique constraint is the real safety net; this just turns
            # its failure into a normal error response instead of a crash.
            db.rollback()
            raise HTTPException(400, "This license number is already registered to another doctor")

    return {"message": "Profile updated"}


# --------- Profile Change Requests (name / hospital / specialization) ---------
# These fields are gated behind admin approval instead of direct edits:
#   - patient: name
#   - doctor: name, hospital, specialization
# Same request -> admin approve/deny shape as /reassignment-request.
PATIENT_REQUESTABLE_FIELDS = {"name"}
# "license_no" here is a report, not a real request - admin never
# auto-applies it on approval (see resolve_profile_change_request).
# It exists so a doctor has an actual way to flag a wrong license
# number instead of just being told "contact admin" with no path to
# do so. Admin still fixes it manually via /admin/doctors/{id}/license.
DOCTOR_REQUESTABLE_FIELDS = {"name", "hospital", "specialization", "license_no"}


class ProfileChangeRequestData(BaseModel):
    field: str
    requested_value: str
    reason: str | None = None


@app.post("/profile/change-request")
def request_profile_change(
    data: ProfileChangeRequestData,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user["role"] == "patient":
        allowed_fields = PATIENT_REQUESTABLE_FIELDS
    elif user["role"] == "doctor":
        allowed_fields = DOCTOR_REQUESTABLE_FIELDS
    else:
        raise HTTPException(403, "Only patients and doctors can request profile changes")

    if data.field not in allowed_fields:
        raise HTTPException(400, f"'{data.field}' cannot be requested for {user['role']}s")

    existing_pending = db.query(ProfileChangeRequest).filter(
        ProfileChangeRequest.account_id == user["id"],
        ProfileChangeRequest.field == data.field,
        ProfileChangeRequest.status == "pending"
    ).first()

    if existing_pending:
        raise HTTPException(400, f"You already have a pending request to change '{data.field}'")

    request_row = ProfileChangeRequest(
        account_id=user["id"],
        role=user["role"],
        field=data.field,
        requested_value=data.requested_value,
        reason=data.reason
    )

    db.add(request_row)
    db.commit()

    return {"message": "Profile change request submitted"}


@app.get("/profile/change-requests")
def my_profile_change_requests(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ProfileChangeRequest).filter(
        ProfileChangeRequest.account_id == user["id"]
    ).order_by(ProfileChangeRequest.created_at.desc()).all()