from sqlalchemy import Column, Integer, String, DateTime, CheckConstraint
from datetime import datetime
from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(String, nullable=False)  # patient, doctor, or admin
    # NOTE: "admin" accounts are never created through /auth/register
    # (which explicitly blocks anything but patient/doctor) - they're
    # created directly via create_admin.py.

    created_at = Column(DateTime, default=datetime.utcnow)

    # Database-level safety net - the app already validates this, but a
    # CHECK constraint means a bad value can never sneak in even from a
    # raw script or manual insert that bypasses the app entirely.
    __table_args__ = (
        CheckConstraint("role IN ('patient', 'doctor', 'admin')", name="ck_accounts_role"),
    )