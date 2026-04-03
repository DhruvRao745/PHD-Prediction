from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
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

    medical_history = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)