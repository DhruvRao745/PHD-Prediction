from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from datetime import datetime
from app.database import Base


class ProfileChangeRequest(Base):
    """Covers profile fields that are too sensitive for direct
    self-service editing:
      - patient: name
      - doctor: name, hospital, specialization
      - doctor: license_no - this one is a REPORT, not a real request;
        approving it never auto-writes the value (see admin/routes.py),
        it's just a way for the doctor to flag a typo to admin, who then
        applies the actual fix via /admin/doctors/{id}/license.

    `role` records which profile table (patient_profiles vs
    doctor_profiles) the approved change should be written to.
    """
    __tablename__ = "profile_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    role = Column(String, nullable=False)          # "patient" or "doctor"
    field = Column(String, nullable=False)          # "name", "hospital", "specialization", or "license_no"
    requested_value = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, default="pending", index=True)  # pending / approved / denied
    # Admin's explanation for the decision - mainly useful on denials, so
    # the doctor/patient isn't just left with "denied" and no reason why.
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('patient', 'doctor')", name="ck_profile_change_requests_role"),
        CheckConstraint(
            "field IN ('name', 'hospital', 'specialization', 'license_no')",
            name="ck_profile_change_requests_field",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'denied')",
            name="ck_profile_change_requests_status",
        ),
    )
