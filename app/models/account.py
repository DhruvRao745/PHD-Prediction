from sqlalchemy import Column, Integer, String, DateTime, Boolean, CheckConstraint
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

    # Brute-force lockout bookkeeping. failed_login_attempts resets to 0
    # on any successful login; locked_until is only ever set once that
    # counter crosses the threshold, and is cleared again on the next
    # successful login. Living on Account (not a separate table) since
    # it's a small, always-one-row-per-account piece of login state.
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime, nullable=True)

    # Optional 2FA (admin-only feature, enforced in the routes, not here).
    # totp_secret is written as soon as setup starts, but totp_enabled
    # only flips to True once the admin proves they scanned it correctly
    # by submitting one real code back - see /auth/2fa/verify-setup.
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False)

    # Database-level safety net - the app already validates this, but a
    # CHECK constraint means a bad value can never sneak in even from a
    # raw script or manual insert that bypasses the app entirely.
    __table_args__ = (
        CheckConstraint("role IN ('patient', 'doctor', 'admin')", name="ck_accounts_role"),
    )