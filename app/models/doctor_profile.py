from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    doctor_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        primary_key=True
    )

    name = Column(String, nullable=False)

    specialization = Column(String)
    hospital = Column(String)

    license_no = Column(String, unique=True)

    created_at = Column(DateTime, default=datetime.utcnow)