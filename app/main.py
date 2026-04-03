from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
from app.registry.model_registry import MODEL_REGISTRY
from app.auth.routes import router as auth_router
from fastapi import Depends
from app.auth.security import get_current_user
from app.database import SessionLocal
from app.models.prediction import Prediction 
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt
import io
from datetime import datetime
from app.deps import get_db
from fastapi import Depends
from app.services.prediction_service import save_prediction
from sqlalchemy.orm import Session
from app.models.patient_profile import PatientProfile
from app.models.doctor_profile import DoctorProfile
from app.models.doctor_patient import DoctorPatient
from app.models.prediction import Prediction
# TODO: fix import issue 
# Ensure project root is on sys.path when running this file directly
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app.core.predictor import predict
except ModuleNotFoundError:
    from core.predictor import predict
# print("Successfully imported predictor module")
app = FastAPI()
app.include_router(auth_router)


class PredictRequest(BaseModel):
    disease: str
    data: dict


# @app.get("/")
# def root():
#     return {"message": "Welcome to the Multiple Disease Prediction API. Use /predict endpoint to get predictions."}

# @app.get("/health")
# def health_check():
#     return {
#         "status": "ok",
#         "service": "multiple-disease-prediction",
#         "message": "Service is running"
#     }


@app.post("/predict")
def predict_api(
    request: PredictRequest,
    user: dict = Depends(get_current_user),    # returns full user object
    db: Session = Depends(get_db)
):
    # 🧠 Run ML model
    result = predict(request.disease, request.data)

    # Extract from nested structure
    risk = result["prediction"]["risk"]
    confidence = result["prediction"]["confidence"]

    # 🧠 Save to PostgreSQL
    save_prediction(
        db=db,
        patient_id=user["id"],   # from JWT payload
        disease=request.disease,
        risk_level=risk,
        probability=confidence,
        input_method="form",
        model_version="v1.0"
    )

    return result

@app.get("/history")
def get_history(
    disease: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    query = db.query(Prediction).filter(
        Prediction.patient_id == user["id"]
    )

    if disease:
        query = query.filter(
            Prediction.disease == disease
        )

    records = query.all()

    return records

@app.get("/dashboard/patient")
def patient_dashboard(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 🔎 Get patient profile
    patient = db.query(PatientProfile).filter(
        PatientProfile.patient_id == user["id"]
    ).first()

    if not patient:
        return {"error": "Patient profile not found"}

    # 🔎 Get predictions
    predictions = db.query(Prediction).filter(
        Prediction.patient_id == patient.id
    ).all()

    return {
        "patient_profile": patient,
        "predictions": predictions
    }

@app.get("/dashboard/doctor")
def doctor_dashboard(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 🔎 Doctor profile
    doctor = db.query(DoctorProfile).filter(
        DoctorProfile.doctor_id == user["id"]
    ).first()

    if not doctor:
        return {"error": "Doctor profile not found"}

    # 🔎 Patients assigned to doctor
    relations = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor.id
    ).all()

    patients_data = []

    for rel in relations:
        patient = db.query(PatientProfile).filter(
            PatientProfile.id == rel.patient_id
        ).first()

        predictions = db.query(Prediction).filter(
            Prediction.patient_id == patient.id
        ).all()

        patients_data.append({
            "patient": patient,
            "predictions": predictions
        })

    return {
        "doctor_profile": doctor,
        "patients": patients_data
    }

# @app.get("/export/text")
# def export_text(user: str = Depends(get_current_user)):
#     db = SessionLocal()

#     records = db.query(Prediction).filter(
#         Prediction.username == user
#     ).all()

#     file_path = f"{user}_health_report.txt"

#     with open(file_path, "w") as f:
#         f.write(f"Health Report for {user}\n\n")

#         for r in records:
#             f.write(f"{r.timestamp} | {r.disease} | {r.result}\n")

#     return FileResponse(file_path, filename=file_path)

@app.get("/export/pdf")
def export_pdf(user: str = Depends(get_current_user)):  

    db = SessionLocal()

    records = db.query(Prediction).filter(
        Prediction.username == user
    ).order_by(Prediction.id.asc()).all()

    if not records:
        return {"message": "No records found"}

    file_path = f"{user}_medical_report.pdf"

    c = canvas.Canvas(file_path, pagesize=letter)
    y = 750

    # 🧑‍⚕️ TITLE
    c.setFont("Helvetica-Bold", 18)
    c.drawString(120, y, "MULTIPLE DISEASE REPORT")

    y -= 40

    # 🧑 PATIENT INFO
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Patient Name: {user}")
    y -= 20

    c.drawString(50, y, f"Report Date: {datetime.now()}")
    y -= 30

    # 📋 SUMMARY TABLE HEADER
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Date")
    c.drawString(200, y, "Disease")
    c.drawString(350, y, "Risk")

    y -= 20
    c.setFont("Helvetica", 11)

    # 🧠 GROUP BY DISEASE
    disease_data = {}

    for r in records:

        # Extract readable risk
        try:
            risk = r.result.split("'risk': '")[1].split("'")[0]
        except:
            risk = "Unknown"

        c.drawString(50, y, r.timestamp.split(" ")[0])
        c.drawString(200, y, r.disease)
        c.drawString(350, y, risk)

        disease_data.setdefault(r.disease, []).append((r.timestamp, risk))

        y -= 18
        if y < 100:
            c.showPage()
            y = 750

    # 🧩 DISEASE-WISE SECTIONS
    c.showPage()
    y = 750

    for disease, data in disease_data.items():

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"{disease.upper()} REPORT")

        y -= 25
        c.setFont("Helvetica", 11)

        for date, risk in data:
            c.drawString(60, y, f"{date} → {risk}")
            y -= 18

            if y < 80:
                c.showPage()
                y = 750

        y -= 20

    c.save()

    return FileResponse(file_path, filename=file_path)
