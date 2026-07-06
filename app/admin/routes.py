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
from app.models.activity_log import ActivityLog
from app.registry.model_registry import MODEL_REGISTRY
from app.services.activity_log_service import log_activity
from app.services.prediction_service import get_risk_summary

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


# ------------------ CROSS-DISEASE RISK SUMMARY (ADMIN) ------------------
# Admin-side equivalent of GET /risk-summary - same underlying helper,
# just allowed to look up any patient by id instead of only "yourself".
# Doctors deliberately don't get an equivalent of this at all (see
# doctor_dashboard() in main.py) - they stay scoped to one disease.
@router.get("/patients/{patient_id}/risk-summary")
def patient_risk_summary(
    patient_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    patient = db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    return {
        "patient_id": patient.patient_id,
        "patient_name": patient.name,
        "summary": get_risk_summary(db, patient_id),
    }


# ------------------ ASSIGN / UNASSIGN ------------------
# Only admin can do this now - doctors lost their self-service
# assign-patient endpoint (removed from main.py).
# Each assignment is scoped to ONE disease - a doctor assigned for
# "heart" only ever sees that patient's heart data, not their full
# history. See doctor_dashboard() in main.py for the query that enforces
# this on the read side.

class AssignPatientData(BaseModel):
    doctor_id: int
    patient_id: int
    disease: str


@router.post("/assign-patient")
def assign_patient(
    data: AssignPatientData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if data.disease not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown disease '{data.disease}'")

    doctor = db.query(Account).filter(Account.id == data.doctor_id, Account.role == "doctor").first()
    if not doctor:
        raise HTTPException(404, "Doctor not found")

    patient = db.query(Account).filter(Account.id == data.patient_id, Account.role == "patient").first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    existing_active = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == data.doctor_id,
        DoctorPatient.patient_id == data.patient_id,
        DoctorPatient.disease == data.disease,
        DoctorPatient.deleted_at.is_(None),
    ).first()

    if existing_active:
        return {"message": "Patient already assigned to this doctor for this disease"}

    # Always insert a fresh row - doctor_patient now has its own surrogate
    # id, so old soft-deleted links for this same pair (if any) just stay
    # in the table as history instead of being overwritten/reactivated.
    # The partial unique index only blocks a second ACTIVE row for the
    # same (doctor, patient, disease), so this can't create a duplicate.
    relation = DoctorPatient(
        doctor_id=data.doctor_id,
        patient_id=data.patient_id,
        disease=data.disease,
    )
    db.add(relation)
    db.flush()  # populates relation.id without committing yet

    log_activity(
        db, admin, "assign_patient",
        f"Assigned Dr. {doctor.username} to patient {patient.username} for {data.disease}",
        target_type="doctor_patient", target_id=relation.id,
    )
    db.commit()

    return {"message": "Patient assigned successfully"}


@router.delete("/unassign/{assignment_id}")
def unassign_patient(
    assignment_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.id == assignment_id,
        DoctorPatient.deleted_at.is_(None),
    ).first()

    if not relation:
        raise HTTPException(404, "Active assignment not found")

    relation.deleted_at = datetime.utcnow()

    doctor = db.query(Account).filter(Account.id == relation.doctor_id).first()
    patient = db.query(Account).filter(Account.id == relation.patient_id).first()
    log_activity(
        db, admin, "unassign_patient",
        f"Unassigned Dr. {doctor.username if doctor else relation.doctor_id} from patient "
        f"{patient.username if patient else relation.patient_id} ({relation.disease})",
        target_type="doctor_patient", target_id=relation.id,
    )
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
            "id": r.id,
            "doctor_id": r.doctor_id,
            "doctor_username": doctor.username if doctor else None,
            "patient_id": r.patient_id,
            "patient_username": patient.username if patient else None,
            "disease": r.disease,
            "assigned_at": r.assigned_at,
        })
    return results


# ------------------ DELETED ASSIGNMENTS: LIST / RESTORE / PURGE ------------------
# These act on the row's own `id` now, not doctor_id+patient_id - since
# the same pair can be linked/unlinked more than once over time, that
# pair alone is no longer enough to point at one specific row.

@router.get("/assignments/deleted")
def list_deleted_assignments(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(DoctorPatient).filter(DoctorPatient.deleted_at.isnot(None)).order_by(
        DoctorPatient.deleted_at.desc()
    ).all()
    results = []
    for r in rows:
        doctor = db.query(Account).filter(Account.id == r.doctor_id).first()
        patient = db.query(Account).filter(Account.id == r.patient_id).first()
        results.append({
            "id": r.id,
            "doctor_id": r.doctor_id,
            "doctor_username": doctor.username if doctor else None,
            "patient_id": r.patient_id,
            "patient_username": patient.username if patient else None,
            "disease": r.disease,
            "assigned_at": r.assigned_at,
            "deleted_at": r.deleted_at,
        })
    return results


@router.patch("/assignments/{assignment_id}/restore")
def restore_assignment(
    assignment_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    relation = db.query(DoctorPatient).filter(
        DoctorPatient.id == assignment_id,
        DoctorPatient.deleted_at.isnot(None),
    ).first()

    if not relation:
        raise HTTPException(404, "Deleted assignment not found")

    # Restoring this one could collide with the one-active-link rule if
    # the same (doctor, patient, disease) already got a different active
    # row in the meantime - guard against that instead of letting the
    # database reject it with a raw constraint error.
    already_active = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == relation.doctor_id,
        DoctorPatient.patient_id == relation.patient_id,
        DoctorPatient.disease == relation.disease,
        DoctorPatient.deleted_at.is_(None),
    ).first()
    if already_active:
        raise HTTPException(400, "This doctor is already actively assigned to this patient for this disease")

    relation.deleted_at = None

    doctor = db.query(Account).filter(Account.id == relation.doctor_id).first()
    patient = db.query(Account).filter(Account.id == relation.patient_id).first()
    log_activity(
        db, admin, "restore_assignment",
        f"Restored assignment: Dr. {doctor.username if doctor else relation.doctor_id} - "
        f"patient {patient.username if patient else relation.patient_id} ({relation.disease})",
        target_type="doctor_patient", target_id=relation.id,
    )
    db.commit()

    return {"message": "Assignment restored"}


@router.delete("/assignments/{assignment_id}/permanent")
def purge_assignment(
    assignment_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    relation = db.query(DoctorPatient).filter(DoctorPatient.id == assignment_id).first()

    if not relation:
        raise HTTPException(404, "Assignment not found")

    doctor = db.query(Account).filter(Account.id == relation.doctor_id).first()
    patient = db.query(Account).filter(Account.id == relation.patient_id).first()
    # Logged before the delete - this row is about to be gone for good,
    # so the log is the only place this record of it survives.
    log_activity(
        db, admin, "purge_assignment",
        f"Permanently deleted assignment: Dr. {doctor.username if doctor else relation.doctor_id} - "
        f"patient {patient.username if patient else relation.patient_id} ({relation.disease})",
        target_type="doctor_patient", target_id=relation.id,
    )

    db.delete(relation)
    db.commit()

    return {"message": "Assignment permanently deleted"}


# ------------------ DELETED PREDICTIONS: LIST / RESTORE / PURGE ------------------

@router.get("/predictions/deleted")
def list_deleted_predictions(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    rows = db.query(Prediction).filter(Prediction.deleted_at.isnot(None)).all()
    results = []
    for p in rows:
        # account here can be a patient OR a doctor (self-predictions) -
        # named generically since this table isn't patient-only anymore.
        account = db.query(Account).filter(Account.id == p.account_id).first()
        results.append({
            "id": p.id,
            "account_id": p.account_id,
            "account_username": account.username if account else None,
            "account_role": account.role if account else None,
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

    account = db.query(Account).filter(Account.id == prediction.account_id).first()
    log_activity(
        db, admin, "restore_prediction",
        f"Restored {prediction.disease} prediction for {account.username if account else prediction.account_id}",
        target_type="prediction", target_id=prediction.id,
    )
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

    account = db.query(Account).filter(Account.id == prediction.account_id).first()
    log_activity(
        db, admin, "purge_prediction",
        f"Permanently deleted {prediction.disease} prediction for "
        f"{account.username if account else prediction.account_id}",
        target_type="prediction", target_id=prediction.id,
    )

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
            "disease": r.disease,
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

    # doctor_id + disease together identify exactly one assignment now,
    # so this only ever unassigns that one - a patient with more than one
    # active doctor (or the same doctor for a different disease) keeps
    # the others untouched.
    if data.status == "approved":
        relation = db.query(DoctorPatient).filter(
            DoctorPatient.doctor_id == req.doctor_id,
            DoctorPatient.patient_id == req.patient_id,
            DoctorPatient.disease == req.disease,
            DoctorPatient.deleted_at.is_(None),
        ).first()
        if relation:
            relation.deleted_at = datetime.utcnow()

    req.status = data.status
    req.admin_note = data.note
    req.resolved_at = datetime.utcnow()

    patient = db.query(Account).filter(Account.id == req.patient_id).first()
    doctor = db.query(Account).filter(Account.id == req.doctor_id).first() if req.doctor_id else None
    log_activity(
        db, admin, "resolve_reassignment_request",
        f"{data.status.capitalize()} reassignment request from patient "
        f"{patient.username if patient else req.patient_id} away from "
        f"Dr. {doctor.username if doctor else req.doctor_id} ({req.disease})",
        target_type="reassignment_request", target_id=req.id,
    )
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

    account = db.query(Account).filter(Account.id == req.account_id).first()
    log_activity(
        db, admin, "resolve_profile_change_request",
        f"{data.status.capitalize()} {account.username if account else req.account_id}'s request to change "
        f"{req.field} to '{req.requested_value}'",
        target_type="profile_change_request", target_id=req.id,
    )
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

    old_value = profile.license_no
    profile.license_no = data.license_no

    log_activity(
        db, admin, "correct_license",
        f"Corrected Dr. {profile.name}'s license number from "
        f"'{old_value or '(unset)'}' to '{data.license_no}'",
        target_type="doctor_profile", target_id=doctor_id,
    )
    db.commit()

    return {"message": "License number corrected"}


# ------------------ ACTIVITY LOG ------------------
# Read-only, admin-only view of every logged action, newest first.
# `action` filters to one action type (e.g. "purge_prediction"); `actor_role`
# filters to who did it. Both optional and combinable. Capped at 200 rows
# per request - this is a browsing view, not a full export.
@router.get("/activity-log")
def list_activity_log(
    action: str | None = None,
    actor_role: str | None = None,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ActivityLog)
    if action:
        query = query.filter(ActivityLog.action == action)
    if actor_role:
        query = query.filter(ActivityLog.actor_role == actor_role)

    rows = query.order_by(ActivityLog.created_at.desc()).limit(200).all()

    return [
        {
            "id": r.id,
            "actor_username": r.actor_username,
            "actor_role": r.actor_role,
            "action": r.action,
            "description": r.description,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
