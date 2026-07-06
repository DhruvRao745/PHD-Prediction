from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from datetime import datetime
from app.database import Base


class ReassignmentRequest(Base):
    """
    A patient's request to be reassigned away from ONE specific doctor.
    Only admin can act on these - approving one soft-deletes that one
    doctor-patient link; admin can then assign a new doctor separately.

    doctor_id is required (not just "whichever doctor happens to be
    active") because doctor_patient is genuinely many-to-many - a
    patient can have more than one active doctor at once (e.g. a heart
    doctor and a kidney doctor), so the request has to say which
    specific one the patient wants to be reassigned away from.
    """

    __tablename__ = "reassignment_requests"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    doctor_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    # Which specific assignment this is about - doctor_patient is scoped
    # per disease now, so doctor_id alone isn't enough to identify one
    # assignment if the same doctor is ever assigned to this patient for
    # more than one disease.
    disease = Column(String, nullable=False)

    reason = Column(String, nullable=True)

    status = Column(String, default="pending", index=True)  # pending / approved / denied

    # Admin's explanation for the decision - mainly useful on denials, so
    # the patient isn't just left with "denied" and no reason why.
    admin_note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'denied')",
            name="ck_reassignment_requests_status",
        ),
        CheckConstraint(
            "disease IN ('diabetes', 'heart', 'parkinsons', 'kidney')",
            name="ck_reassignment_requests_disease",
        ),
    )
