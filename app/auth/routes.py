from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.deps import get_db
from app.models.account import Account
from .security import (
    hash_password, verify_password, create_token, create_pending_2fa_token,
    get_current_user, get_current_admin,
)
from jose import jwt, JWTError
from .security import SECRET_KEY, ALGORITHM
from app.services.twofa_service import (
    generate_totp_secret, build_qr_code_data_uri, verify_totp_code,
    generate_backup_codes, store_backup_codes, verify_and_consume_backup_code,
)
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.backup_code import BackupCode
from app.services.activity_log_service import log_activity
from app.services.password_reset_service import create_reset_token, get_valid_token, consume_token
from app.services.email_service import send_password_reset_email
from app.config import FRONTEND_URL, RESET_TOKEN_EXPIRE_MINUTES, MAX_LOGIN_ATTEMPTS, LOCKOUT_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterData(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str   # "patient" or "doctor"


class ChangePasswordData(BaseModel):
    current_password: str
    new_password: str


class EmailUpdateData(BaseModel):
    email: EmailStr


class ForgotPasswordData(BaseModel):
    email: EmailStr


class ResetPasswordData(BaseModel):
    token: str
    new_password: str

# -------- REGISTER --------
@router.post("/register")
def register(user: RegisterData, db: Session = Depends(get_db)):

    # Check existing username
    existing = db.query(Account).filter(
        Account.username == user.username
    ).first()

    if existing:
        raise HTTPException(400, "Username already exists")

    # Real email now required (not the old f"{username}@example.com"
    # placeholder) - forgot-password has nowhere to send a link without one.
    existing_email = db.query(Account).filter(
        Account.email == user.email
    ).first()

    if existing_email:
        raise HTTPException(400, "An account with this email already exists")

    if user.role not in ["patient", "doctor"]:
        raise HTTPException(400, "Role must be patient or doctor")

    # Create account
    new_user = Account(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create role-specific profile
    if user.role == "patient":

        profile = PatientProfile(
            patient_id=new_user.id,
            name=user.username
        )

    else:  # doctor

        profile = DoctorProfile(
            doctor_id=new_user.id,
            name=user.username
        )

    db.add(profile)

    # The actor here is the account that just registered itself - there's
    # no separate "admin created this" actor for self-service signup.
    log_activity(
        db, {"id": new_user.id, "username": new_user.username, "role": new_user.role},
        "register", f"{new_user.username} registered as a {user.role}",
        target_type="account", target_id=new_user.id,
    )
    db.commit()

    return {"message": f"{user.role} registered successfully"}

# -------- LOGIN --------

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    db_user = db.query(Account).filter(
        Account.username == form_data.username
    ).first()

    # Locked accounts are rejected before the password is even checked -
    # otherwise a locked-out attacker could still use this endpoint to
    # keep guessing, just without ever getting a token back.
    if db_user and db_user.locked_until and db_user.locked_until > datetime.utcnow():
        minutes_left = max(1, int((db_user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1)
        raise HTTPException(
            423,
            f"Too many failed attempts - this account is locked for about {minutes_left} more minute(s)",
        )

    if not db_user or not verify_password(
        form_data.password, db_user.password_hash
    ):
        if db_user:
            db_user.failed_login_attempts += 1
            if db_user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                db_user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                log_activity(
                    db, {"id": db_user.id, "username": db_user.username, "role": db_user.role},
                    "account_locked",
                    f"{db_user.username} was locked out after {MAX_LOGIN_ATTEMPTS} failed login attempts",
                    target_type="account", target_id=db_user.id,
                )
            db.commit()
        raise HTTPException(401, "Invalid credentials")

    # Successful login - clear any lockout bookkeeping.
    if db_user.failed_login_attempts or db_user.locked_until:
        db_user.failed_login_attempts = 0
        db_user.locked_until = None
        db.commit()

    # Password was correct, but 2FA-enabled accounts don't get a real
    # access token yet - just a short-lived pending token that only
    # /auth/2fa/login-verify can redeem, once the TOTP/backup code checks out.
    if db_user.totp_enabled:
        return {
            "requires_2fa": True,
            "pending_token": create_pending_2fa_token(db_user.id),
        }

    token = create_token(db_user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }

# -------- CURRENT USER --------
# Used by the frontend right after login to find out the user's
# id/role/username, since the JWT itself only carries the user id.
@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return user


# -------- CHANGE PASSWORD --------
# Works the same for patient, doctor, or admin accounts - password
# lives on Account, not on the role-specific profile tables, so there's
# nothing role-specific about changing it.
@router.post("/change-password")
def change_password(
    data: ChangePasswordData,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == user["id"]).first()

    if not account or not verify_password(data.current_password, account.password_hash):
        raise HTTPException(401, "Current password is incorrect")

    # TEMP-DISABLED for testing convenience - RE-ENABLE before launch:
    # if len(data.new_password) < 6:
    #     raise HTTPException(400, "New password must be at least 6 characters")

    account.password_hash = hash_password(data.new_password)

    log_activity(
        db, user, "change_password", f"{user['username']} changed their password",
        target_type="account", target_id=user["id"],
    )
    db.commit()

    return {"message": "Password changed successfully"}


# -------- UPDATE EMAIL --------
# Same "works for any role" reasoning as change-password - this is what
# lets an admin (who has no profile page of their own) fix up their real
# email too, not just patients/doctors. Also the only way an existing
# account (created back when registration faked emails) gets a real one.
@router.patch("/account/email")
def update_email(
    data: EmailUpdateData,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == user["id"]).first()

    if not account:
        raise HTTPException(404, "Account not found")

    duplicate = db.query(Account).filter(
        Account.email == data.email,
        Account.id != user["id"],
    ).first()
    if duplicate:
        raise HTTPException(400, "This email is already in use by another account")

    account.email = data.email

    log_activity(
        db, user, "update_email", f"{user['username']} changed their email",
        target_type="account", target_id=user["id"],
    )
    db.commit()

    return {"message": "Email updated successfully", "email": account.email}


# -------- FORGOT PASSWORD --------
# Deliberately returns the exact same message whether or not the email
# actually matches an account - otherwise this endpoint becomes a free
# "does this email have an account here" oracle for anyone who tries it.
@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordData, db: Session = Depends(get_db)):
    generic_message = (
        "If that email is registered, we've sent password reset instructions to it."
    )

    account = db.query(Account).filter(Account.email == data.email).first()

    if account:
        token = create_reset_token(db, account.id)
        reset_link = f"{FRONTEND_URL}/reset-password?token={token.token}"

        # Doubles as "forgot username" - the email always includes the
        # account's username too, so there's no separate flow needed for
        # someone who only forgot their username, not their password.
        send_password_reset_email(
            account.email, account.username, reset_link, RESET_TOKEN_EXPIRE_MINUTES
        )

        log_activity(
            db, {"id": account.id, "username": account.username, "role": account.role},
            "forgot_password_requested", f"{account.username} requested a password reset",
            target_type="account", target_id=account.id,
        )
        db.commit()

    return {"message": generic_message}


# -------- RESET PASSWORD --------
@router.post("/reset-password")
def reset_password(data: ResetPasswordData, db: Session = Depends(get_db)):
    token_row = get_valid_token(db, data.token)

    if not token_row:
        raise HTTPException(400, "This reset link is invalid or has expired - request a new one")

    account = db.query(Account).filter(Account.id == token_row.account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")

    # TEMP-DISABLED for testing convenience, matching change-password -
    # RE-ENABLE before launch (see app/auth/routes.py change_password too):
    # if len(data.new_password) < 6:
    #     raise HTTPException(400, "New password must be at least 6 characters")

    account.password_hash = hash_password(data.new_password)
    # A successful reset proves account ownership, same as a correct
    # password would - clear any lockout so a locked-out user isn't
    # stuck waiting even after fixing their password.
    account.failed_login_attempts = 0
    account.locked_until = None
    consume_token(db, token_row)

    log_activity(
        db, {"id": account.id, "username": account.username, "role": account.role},
        "password_reset", f"{account.username} reset their password via email link",
        target_type="account", target_id=account.id,
    )
    db.commit()

    return {"message": "Password reset successfully - you can now log in with your new password"}


# ==================== TWO-FACTOR AUTH (ADMIN-ONLY) ====================
# Opt-in, not forced - any admin can turn it on for their own account from
# Account Settings, but create_admin.py / registration don't require it.
# Scoped to admin only: patients/doctors never see any of this.

class TwoFAVerifySetupData(BaseModel):
    code: str


class TwoFALoginVerifyData(BaseModel):
    pending_token: str
    code: str


class TwoFADisableData(BaseModel):
    password: str


@router.post("/2fa/setup")
def setup_2fa(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == admin["id"]).first()
    if not account:
        raise HTTPException(404, "Account not found")

    if account.totp_enabled:
        raise HTTPException(400, "2FA is already enabled - disable it first to re-set-up")

    # Written now but not "on" yet - totp_enabled only flips once the
    # admin proves the scan worked by submitting one real code back via
    # /2fa/verify-setup. Overwrites any previous unfinished attempt.
    secret = generate_totp_secret()
    account.totp_secret = secret
    db.commit()

    return {
        "secret": secret,
        "qr_code": build_qr_code_data_uri(secret, account.username),
    }


@router.post("/2fa/verify-setup")
def verify_setup_2fa(
    data: TwoFAVerifySetupData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == admin["id"]).first()
    if not account or not account.totp_secret:
        raise HTTPException(400, "No 2FA setup in progress - call /2fa/setup first")

    if not verify_totp_code(account.totp_secret, data.code):
        raise HTTPException(400, "That code didn't match - check your authenticator app and try again")

    account.totp_enabled = True
    backup_codes = generate_backup_codes()
    store_backup_codes(db, account.id, backup_codes)

    log_activity(
        db, admin, "2fa_enabled", f"{admin['username']} enabled two-factor authentication",
        target_type="account", target_id=account.id,
    )
    db.commit()

    # Only time these plaintext codes are ever returned - only their
    # bcrypt hashes exist in the database from this point on.
    return {
        "message": "2FA enabled successfully",
        "backup_codes": backup_codes,
    }


@router.post("/2fa/disable")
def disable_2fa(
    data: TwoFADisableData,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == admin["id"]).first()
    if not account or not verify_password(data.password, account.password_hash):
        raise HTTPException(401, "Current password is incorrect")

    account.totp_enabled = False
    account.totp_secret = None
    db.query(BackupCode).filter(BackupCode.account_id == account.id).delete()

    log_activity(
        db, admin, "2fa_disabled", f"{admin['username']} disabled two-factor authentication",
        target_type="account", target_id=account.id,
    )
    db.commit()

    return {"message": "2FA disabled"}


@router.post("/2fa/login-verify")
def login_verify_2fa(data: TwoFALoginVerifyData, db: Session = Depends(get_db)):
    # Decoded by hand (not via get_current_user) since a pending token is
    # explicitly NOT a valid access token - this is the one place it's
    # allowed to be used, and only for this one purpose.
    try:
        payload = jwt.decode(data.pending_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "This 2FA session has expired - log in again")

    if payload.get("type") != "2fa_pending":
        raise HTTPException(401, "Invalid session - log in again")

    user_id = payload.get("sub")
    account = db.query(Account).filter(Account.id == int(user_id)).first()
    if not account or not account.totp_enabled:
        raise HTTPException(401, "Invalid session - log in again")

    code = data.code.strip().replace(" ", "")
    valid = verify_totp_code(account.totp_secret, code) or verify_and_consume_backup_code(
        db, account.id, code
    )

    if not valid:
        raise HTTPException(401, "Invalid code")

    log_activity(
        db, {"id": account.id, "username": account.username, "role": account.role},
        "2fa_login_success", f"{account.username} completed 2FA login",
        target_type="account", target_id=account.id,
    )
    db.commit()

    token = create_token(account.id)
    return {"access_token": token, "token_type": "bearer"}