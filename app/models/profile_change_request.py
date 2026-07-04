from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class ProfileChangeRequest(Base):
    """Covers profile fields that are too sensitive for direct
    self-service editing:
      - patient: name
      - doctor: name, hospital, specialization
    (doctor license_no is handled separately - it's not requestable at
    all, only admin can correct it directly, see /admin/doctors/{id}/license)

    `role` records which profile table (patient_profiles vs
    doctor_profiles) the approved change should be written to.
    """
    __tablename__ = "profile_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    role = Column(String, nullable=False)          # "patient" or "doctor"
    field = Column(String, nullable=False)          # "name", "hospital", or "specialization"
    requested_value = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, default="pending")      # pending / approved / denied
    # Admin's explanation for the decision - mainly useful on denials, so
    # the doctor/patient isn't just left with "denied" and no reason why.
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
