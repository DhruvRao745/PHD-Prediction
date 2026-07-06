from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint
from datetime import datetime
from app.database import Base


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    patient_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        primary_key=True
    )

    name = Column(String, nullable=False)
    age = Column(Integer)
    gender = Column(String)

    height_cm = Column(Float)
    weight_kg = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    # gender is nullable (profile might not be filled in yet), but if a
    # value IS given, it has to be one the frontend actually offers -
    # CHECK constraints skip NULLs automatically, so this doesn't block
    # an empty profile.
    __table_args__ = (
        CheckConstraint("gender IN ('male', 'female', 'other')", name="ck_patient_profiles_gender"),
    )