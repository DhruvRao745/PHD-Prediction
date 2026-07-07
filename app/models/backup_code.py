from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class BackupCode(Base):
    """One-time-use fallback codes for when a 2FA-enabled admin loses
    access to their authenticator app. Stored hashed (same bcrypt context
    as account passwords) rather than in plain text, same reasoning as
    password_hash - if this table ever leaked, the codes still couldn't
    be used directly.

    A fresh batch fully replaces the old one every time 2FA is set up
    (or re-set-up), so there's never ambiguity about which batch is
    "the current one" for an account.
    """

    __tablename__ = "backup_codes"

    id = Column(Integer, primary_key=True, index=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    code_hash = Column(String, nullable=False)

    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
