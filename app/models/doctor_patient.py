from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, CheckConstraint, text
from datetime import datetime
from app.database import Base


class DoctorPatient(Base):
    __tablename__ = "doctor_patient"

    # Own surrogate ID instead of (doctor_id, patient_id) as the primary
    # key. The old composite-key design meant a doctor+patient pair could
    # only ever exist once in the whole table, so reassigning the same
    # pair after an unassign had to overwrite assigned_at instead of
    # keeping a new row - that erased assignment history. With a
    # surrogate ID, old soft-deleted rows just stay in the table.
    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    # Which disease this specific assignment covers - a doctor assigned
    # for "heart" only sees that patient's heart predictions, not their
    # entire history. This also means the same doctor+patient pair can
    # legitimately have more than one active row if the same doctor is
    # separately assigned for two different diseases.
    disease = Column(String, nullable=False)

    assigned_at = Column(DateTime, default=datetime.utcnow)

    # Soft delete: NULL = active assignment. Only admin can assign/unassign
    # (soft-delete) doctor-patient links, and only admin can restore or
    # permanently hard-delete one.
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        # Only one ACTIVE link per (doctor, patient, disease) at a time -
        # a partial unique index (only applies where deleted_at IS NULL),
        # so old, unassigned rows don't block a brand new active row.
        Index(
            "uq_active_doctor_patient_disease",
            "doctor_id", "patient_id", "disease",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "disease IN ('diabetes', 'heart', 'parkinsons', 'kidney')",
            name="ck_doctor_patient_disease",
        ),
    )
