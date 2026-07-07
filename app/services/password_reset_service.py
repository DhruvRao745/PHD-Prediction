import secrets
from datetime import datetime, timedelta

from app.models.password_reset_token import PasswordResetToken
from app.config import RESET_TOKEN_EXPIRE_MINUTES


def create_reset_token(db, account_id: int) -> PasswordResetToken:
    """Makes a fresh single-use token for this account. Doesn't bother
    invalidating older unused tokens for the same account - they'll
    simply expire on their own, and letting them coexist keeps this
    function simple (no risk of accidentally revoking a link the user
    is mid-way through using in another tab).
    """
    token = PasswordResetToken(
        account_id=account_id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_token(db, token_str: str) -> PasswordResetToken | None:
    """Returns the token row only if it's real, unused, and unexpired -
    None for every other case, so callers can't accidentally tell an
    attacker *why* a token failed (expired vs. already used vs. never
    existed all look identical from the outside).
    """
    row = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token_str
    ).first()

    if not row:
        return None
    if row.used_at is not None:
        return None
    if row.expires_at < datetime.utcnow():
        return None

    return row


def consume_token(db, token_row: PasswordResetToken):
    """Marks a token used - caller commits afterward, same transaction
    as the password change itself, so a crash between the two can never
    leave a token burned with no password actually changed (or vice versa).
    """
    token_row.used_at = datetime.utcnow()
