from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class ReassignmentRequest(Base):
    """
    A patient's request to be reassigned away from their current doctor.
    Only admin can act on these - approving one soft-deletes the current
    doctor-patient link; admin can then assign a new doctor separately.
    """

    __tablename__ = "reassignment_requests"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)

    # The doctor being reassigned away from, if the patient had one
    # assigned at the time of the request.
    doctor_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    reason = Column(String, nullable=True)

    status = Column(String, default="pending")  # pending / approved / denied

    # Admin's explanation for the decision - mainly useful on denials, so
    # the patient isn't just left with "denied" and no reason why.
    admin_note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
