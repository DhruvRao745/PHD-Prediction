from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models.account import Account

SECRET_KEY = "supersecretkey"   # ONLY ONE
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(minutes=60)
    payload = {"sub": str(user_id), "exp": expire}   # IMPORTANT: string
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Issued instead of a real access token when a password check passes but
# the account still needs to submit a 2FA code. Deliberately short-lived
# and tagged with "type": "2fa_pending" so it can't be used anywhere a
# normal access token would be accepted - see the check in
# get_current_user() below and its use in /auth/2fa/login-verify.
def create_pending_2fa_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": str(user_id), "exp": expire, "type": "2fa_pending"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        # A 2fa_pending token proves the password was correct, nothing
        # more - it must never work as a substitute for a real login.
        if payload.get("type") == "2fa_pending":
            raise HTTPException(status_code=401, detail="2FA verification required")

        user = db.query(Account).filter(Account.id == int(user_id)).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "id": user.id,
            "role": user.role,
            "username": user.username,
            "email": user.email,
            "totp_enabled": user.totp_enabled,
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_admin(user: dict = Depends(get_current_user)):
    """Same as get_current_user, but rejects anyone who isn't an admin.
    Use this instead of get_current_user on admin-only routes so the
    role check doesn't need to be repeated in every route body."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user