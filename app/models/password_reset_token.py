from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class PasswordResetToken(Base):
    """A one-time-use code emailed to an account so it can prove it owns
    that inbox without ever typing its real password anywhere insecure.

    Each row is single-use: `used_at` gets stamped the moment it's
    redeemed, and `expires_at` caps how long an unused link stays valid
    (short window, so a stale, unread email can't be used months later).
    Old accounts aren't deleted - keeping them around is a cheap audit
    trail of "someone tried to reset this account's password on X date".
    """

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)

    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)

    # Random opaque string (secrets.token_urlsafe) - not a JWT on purpose,
    # since it needs to be trivially revocable/single-use via a DB row,
    # not just self-validating like the login token is.
    token = Column(String, unique=True, nullable=False, index=True)

    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
