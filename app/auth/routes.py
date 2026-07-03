from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import SessionLocal
from app.models.account import Account
from .security import hash_password, verify_password, create_token, get_current_user
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterData(BaseModel):
    username: str
    password: str
    role: str   # "patient" or "doctor"

# -------- REGISTER --------
@router.post("/register")
def register(user: RegisterData):

    db = SessionLocal()

    # Check existing username
    existing = db.query(Account).filter(
        Account.username == user.username
    ).first()

    if existing:
        raise HTTPException(400, "Username already exists")

    if user.role not in ["patient", "doctor"]:
        raise HTTPException(400, "Role must be patient or doctor")

    # Create account
    new_user = Account(
        username=user.username,
        email=f"{user.username}@example.com",
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
    db.commit()

    return {"message": f"{user.role} registered successfully"}

# -------- LOGIN --------

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    db = SessionLocal()

    db_user = db.query(Account).filter(
        Account.username == form_data.username
    ).first()

    if not db_user or not verify_password(
        form_data.password, db_user.password_hash
    ):
        raise HTTPException(401, "Invalid credentials")

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