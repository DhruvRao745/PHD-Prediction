"""TOTP (authenticator app) two-factor auth for admin accounts, plus the
one-time backup codes that cover "I lost my phone".

Deliberately kept separate from security.py - that file is about proving
identity via password + JWT; this one is specifically about the second
factor, so the two can be read (and changed) independently.
"""
import base64
import io
import secrets
from datetime import datetime

import pyotp
import qrcode

from app.auth.security import hash_password, verify_password
from app.models.backup_code import BackupCode

ISSUER_NAME = "P.H.D. Prediction"
BACKUP_CODE_COUNT = 8


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_qr_code_data_uri(secret: str, username: str) -> str:
    """Returns a data: URI the frontend can drop straight into an <img
    src>, so the backend never has to serve a separate image endpoint
    just for this one QR code.
    """
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER_NAME)

    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def verify_totp_code(secret: str, code: str) -> bool:
    # valid_window=1 tolerates the code from one 30s step before/after
    # now, since phone and server clocks are never perfectly in sync.
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_backup_codes() -> list[str]:
    """Plain-text codes - only ever returned to the caller once, at
    generation time. Never stored anywhere except as a bcrypt hash.
    """
    return [f"{secrets.token_hex(4)}" for _ in range(BACKUP_CODE_COUNT)]


def store_backup_codes(db, account_id: int, plain_codes: list[str]):
    """Replaces any existing backup codes for this account with a fresh
    batch - old codes from a previous 2FA setup stop working the moment
    2FA is re-enabled, so there's never two "current" batches at once.
    """
    db.query(BackupCode).filter(BackupCode.account_id == account_id).delete()
    for code in plain_codes:
        db.add(BackupCode(account_id=account_id, code_hash=hash_password(code)))


def verify_and_consume_backup_code(db, account_id: int, code: str) -> bool:
    unused = db.query(BackupCode).filter(
        BackupCode.account_id == account_id,
        BackupCode.used_at.is_(None),
    ).all()

    for row in unused:
        if verify_password(code, row.code_hash):
            row.used_at = datetime.utcnow()
            return True

    return False
