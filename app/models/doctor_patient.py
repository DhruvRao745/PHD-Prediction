from sqlalchemy import Column, Integer, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class DoctorPatient(Base):
    __tablename__ = "doctor_patient"

    doctor_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        primary_key=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        primary_key=True
    )

    assigned_at = Column(DateTime, default=datetime.utcnow)

    # Soft delete: NULL = active assignment. Only admin can assign/unassign
    # (soft-delete) doctor-patient links, and only admin can restore or
    # permanently hard-delete one.
    deleted_at = Column(DateTime, nullable=True)