from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.auth.security import get_current_admin
from app.models.account import Account
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_patient import DoctorPatient
from app.models.prediction import Prediction
from app.models.reassignment_request import ReassignmentRequest
from app.models.profile_change_request import ProfileChangeRequest

router = APIRouter(prefix="/admin", tags=["Admin"])


# ------------------ LIST DOCTORS / PATIENTS ------------------
# So the admin portal has something to pick from instead of requiring
# raw account IDs typed blind (the gap the old doctor-side assign flow had).

@router.get("/doctors")
def list_doctors(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    doctors = db.query(DoctorProfile).all()
    return [
        {
            "doctor_id": d.doctor_id,
            "name": d.name,
            "specialization": d.specialization,
            "hospital": d.hospital,
        }
        for d in doctors
    ]


@router.get("/patients")
def list_patients(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    patients = db.query(PatientProfile).all()
    return [
        {
            "patient_id": p.patient_id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender,
        }
        for p in patients
    ]


# ------------------ ASSIGN / UNASSIGN ------------------
# Only admin can do this now - doctors lost their self-service
# assign-patient endpoint (removed from main.py).

class AssignPatientData(BaseModel):
    doctor_id: int
    patient_id: int


@router.post("/assign-patient")
def assign_patient(
    data: AssignPatientData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    doctor = db.query(Account).filter(Account.id == data.doctor_id, Account.role == "doctor").first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    patient = db.query(Account).filter(Account.id == data.patient_id, Account.role == "patient").first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    existing = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == data.doctor_id,
        DoctorPatient.patient_id == data.patient_id,
    ).first()

    if existing:
        if existing.deleted_at is None:
            return {"message": "Patient already assigned to this doctor"}
        # Was previously unassigned - reactivate rather than insert a
        # duplicate row (doctor_id+patient_id is the composite PK).
        existing.deleted_at = None
        existing.assigned_at = datetime.utcnow()
        db.commit()
        return {"message": "Patient reassigned to doctor"}

    relation = DoctorPatient(doctor_id=data.doctor_id, patient_id=data.patient_id)
    db.add(relation)
    db.commit()

    return {"message": "Patient assigned successfully"}


@router.delete("/unassign/{doctor_id}/{patient_id}")
def unassign_patient(
    doctor_id: int,
    patient_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor_id,
        DoctorPatient.patient_id == patient_id,
        DoctorPatient.deleted_at.is_(None),
    ).first()

    if not relation:
        raise HTTPException(404, "Active assignment not found")

    relation.deleted_at = datetime.utcnow()
    db.commit()

    return {"message": "Patient unassigned"}


# ------------------ ACTIVE ASSIGNMENTS ------------------

@router.get("/assignments")
def list_active_assignments(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(DoctorPatient).filter(DoctorPatient.deleted_at.is_(None)).all()
    results = []
    for r in rows:
        doctor = db.query(Account).filter(Account.id == r.doctor_id).first()
        patient = db.query(Account).filter(Account.id == r.patient_id).first()
        results.append({
            "doctor_id": r.doctor_id,
            "doctor_username": doctor.username if doctor else None,
            "patient_id": r.patient_id,
            "patient_username": patient.username if patient else None,
            "assigned_at": r.assigned_at,
        })
    return results


# ------------------ DELETED ASSIGNMENTS: LIST / RESTORE / PURGE ------------------

@router.get("/assignments/deleted")
def list_deleted_assignments(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(DoctorPatient).filter(DoctorPatient.deleted_at.isnot(None)).all()
    results = []
    for r in rows:
        doctor = db.query(Account).filter(Account.id == r.doctor_id).first()
        patient = db.query(Account).filter(Account.id == r.patient_id).first()
        results.append({
            "doctor_id": r.doctor_id,
            "doctor_username": doctor.username if doctor else None,
            "patient_id": r.patient_id,
            "patient_username": patient.username if patient else None,
            "assigned_at": r.assigned_at,
            "deleted_at": r.deleted_at,
        })
    return results


@router.patch("/assignments/{doctor_id}/{patient_id}/restore")
def restore_assignment(
    doctor_id: int,
    patient_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor_id,
        DoctorPatient.patient_id == patient_id,
        DoctorPatient.deleted_at.isnot(None),
    ).first()

    if not relation:
        raise HTTPException(404, "Deleted assignment not found")

    relation.deleted_at = None
    db.commit()

    return {"message": "Assignment restored"}


@router.delete("/assignments/{doctor_id}/{patient_id}/permanent")
def purge_assignment(
    doctor_id: int,
    patient_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor_id,
        DoctorPatient.patient_id == patient_id,
    ).first()

    if not relation:
        raise HTTPException(404, "Assignment not found")

    db.delete(relation)
    db.commit()

    return {"message": "Assignment permanently deleted"}


# ------------------ DELETED PREDICTIONS: LIST / RESTORE / PURGE ------------------

@router.get("/predictions/deleted")
def list_deleted_predictions(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(Prediction).filter(Prediction.deleted_at.isnot(None)).all()
    results = []
    for p in rows:
        patient = db.query(Account).filter(Account.id == p.patient_id).first()
        results.append({
            "id": p.id,
            "patient_id": p.patient_id,
            "patient_username": patient.username if patient else None,
            "disease": p.disease,
            "risk_level": p.risk_level,
            "probability": p.probability,
            "created_at": p.created_at,
            "deleted_at": p.deleted_at,
        })
    return results


@router.patch("/predictions/{prediction_id}/restore")
def restore_prediction(
    prediction_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.deleted_at.isnot(None),
    ).first()

    if not prediction:
        raise HTTPException(404, "Deleted prediction not found")

    prediction.deleted_at = None
    db.commit()

    return {"message": "Prediction restored"}


@router.delete("/predictions/{prediction_id}/permanent")
def purge_prediction(
    prediction_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()

    if not prediction:
        raise HTTPException(404, "Prediction not found")

    db.delete(prediction)
    db.commit()

    return {"message": "Prediction permanently deleted"}


# ------------------ REASSIGNMENT REQUESTS ------------------

@router.get("/reassignment-requests")
def list_reassignment_requests(
    status: str | None = None,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ReassignmentRequest)
    if status:
        query = query.filter(ReassignmentRequest.status == status)
    else:
        query = query.filter(ReassignmentRequest.status == "pending")

    rows = query.order_by(ReassignmentRequest.created_at.desc()).all()

    results = []
    for r in rows:
        patient = db.query(Account).filter(Account.id == r.patient_id).first()
        doctor = db.query(Account).filter(Account.id == r.doctor_id).first() if r.doctor_id else None
        results.append({
            "id": r.id,
            "patient_id": r.patient_id,
            "patient_username": patient.username if patient else None,
            "doctor_id": r.doctor_id,
            "doctor_username": doctor.username if doctor else None,
            "reason": r.reason,
            "status": r.status,
            "admin_note": r.admin_note,
            "created_at": r.created_at,
            "resolved_at": r.resolved_at,
        })
    return results


class ResolveRequestData(BaseModel):
    status: str  # "approved" or "denied"
    # Admin's explanation for the decision. Not required, but the whole
    # point of adding this is so a denial doesn't just say "denied" with
    # zero context for the person who asked.
    note: str | None = None


@router.patch("/reassignment-requests/{request_id}")
def resolve_reassignment_request(
    request_id: int,
    data: ResolveRequestData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if data.status not in ["approved", "denied"]:
        raise HTTPException(400, "Status must be 'approved' or 'denied'")

    req = db.query(ReassignmentRequest).filter(ReassignmentRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")

    if req.status != "pending":
        raise HTTPException(400, f"Request already {req.status}")

    if data.status == "approved" and req.doctor_id is not None:
        relation = db.query(DoctorPatient).filter(
            DoctorPatient.doctor_id == req.doctor_id,
            DoctorPatient.patient_id == req.patient_id,
            DoctorPatient.deleted_at.is_(None),
        ).first()
        if relation:
            relation.deleted_at = datetime.utcnow()

    req.status = data.status
    req.admin_note = data.note
    req.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": f"Request {data.status}"}


# ------------------ PROFILE CHANGE REQUESTS ------------------
# name (patient/doctor) and hospital/specialization (doctor) all route
# through here instead of a direct self-edit - see /profile/change-request.

@router.get("/profile-change-requests")
def list_profile_change_requests(
    status: str | None = None,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ProfileChangeRequest)
    if status:
        query = query.filter(ProfileChangeRequest.status == status)
    else:
        query = query.filter(ProfileChangeRequest.status == "pending")

    rows = query.order_by(ProfileChangeRequest.created_at.desc()).all()

    results = []
    for r in rows:
        account = db.query(Account).filter(Account.id == r.account_id).first()
        results.append({
            "id": r.id,
            "account_id": r.account_id,
            "username": account.username if account else None,
            "role": r.role,
            "field": r.field,
            "requested_value": r.requested_value,
            "reason": r.reason,
            "status": r.status,
            "admin_note": r.admin_note,
            "created_at": r.created_at,
            "resolved_at": r.resolved_at,
        })
    return results


@router.patch("/profile-change-requests/{request_id}")
def resolve_profile_change_request(
    request_id: int,
    data: ResolveRequestData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if data.status not in ["approved", "denied"]:
        raise HTTPException(400, "Status must be 'approved' or 'denied'")

    req = db.query(ProfileChangeRequest).filter(ProfileChangeRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")

    if req.status != "pending":
        raise HTTPException(400, f"Request already {req.status}")

    # license_no reports are never auto-applied, even on approval - a
    # doctor reporting "I think it should be X" isn't authoritative
    # enough on its own. Admin must apply the actual fix separately via
    # /admin/doctors/{doctor_id}/license, after however they choose to
    # verify it. Approving here just acknowledges/closes the report.
    if data.status == "approved" and req.field != "license_no":
        if req.role == "patient":
            profile = db.query(PatientProfile).filter(
                PatientProfile.patient_id == req.account_id
            ).first()
        else:
            profile = db.query(DoctorProfile).filter(
                DoctorProfile.doctor_id == req.account_id
            ).first()

        if profile:
            setattr(profile, req.field, req.requested_value)

    req.status = data.status
    req.admin_note = data.note
    req.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": f"Request {data.status}"}


# ------------------ DIRECT LICENSE CORRECTION ------------------
# license_no is permanently locked from the doctor's own side once set -
# this is the only way to fix a typo, and it's deliberately admin-only.
class LicenseCorrectionData(BaseModel):
    license_no: str


@router.patch("/doctors/{doctor_id}/license")
def correct_doctor_license(
    doctor_id: int,
    data: LicenseCorrectionData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    profile = db.query(DoctorProfile).filter(DoctorProfile.doctor_id == doctor_id).first()
    if not profile:
        raise HTTPException(404, "Doctor profile not found")

    profile.license_no = data.license_no
    db.commit()

    return {"message": "License number corrected"}
