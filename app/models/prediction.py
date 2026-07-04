from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=False
    )

    disease = Column(String, nullable=False)

    risk_level = Column(String)        # Low / Moderate / High
    probability = Column(Float)        # Raw model output

    input_method = Column(String)      # form / questionnaire / upload

    model_version = Column(String)     # e.g., v1.0

    created_at = Column(DateTime, default=datetime.utcnow)

    # Soft delete: NULL = active. Patients/doctors can soft-delete their
    # own predictions; only admin can restore or permanently hard-delete.
    deleted_at = Column(DateTime, nullable=True)