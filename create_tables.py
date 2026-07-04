from app.database import engine, Base

# Import models so SQLAlchemy knows them
from app.models.account import Account
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_patient import DoctorPatient
from app.models.prediction import Prediction
from app.models.reassignment_request import ReassignmentRequest
from app.models.profile_change_request import ProfileChangeRequest

Base.metadata.create_all(bind=engine)

print("✅ Tables created successfully!")