import joblib
import os
from app.utils.validation import check_missing_fields, check_numeric_fields, validate_numeric, validate_schema
from app.utils.schemas import DIABETES_SCHEMA



CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up 3 levels: diabetes -> models -> ml -> app
APP_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)

MODEL_PATH = os.path.join(APP_DIR, "artifacts", "diabetes_model.joblib")

diabetes_model = joblib.load(MODEL_PATH)
# ================================
# 🧠 Required Fields
# ================================
DIABETES_REQUIRED_FIELDS = [
    "Age",
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction"
]

# ================================
# 🏥 Realistic Medical Ranges
# ================================
DIABETES_RANGES = {
    "Age": (0, 120),
    "Pregnancies": (0, 20),
    "Glucose": (0, 300),
    "BloodPressure": (0, 200),
    "SkinThickness": (0, 100),
    "Insulin": (0, 900),
    "BMI": (0, 70),
    "DiabetesPedigreeFunction": (0, 3)
}

def validate_diabetes_input(data):

    errors = validate_schema(data, DIABETES_SCHEMA)

    if errors:
        return {"error": errors}

    return None

def real_diabetes_model(data):
    validation_error = validate_diabetes_input(data)
    if validation_error:
        return validation_error

    features = [[
        data["Age"],
        data["Pregnancies"],
        data["Glucose"],
        data["BloodPressure"],
        data["SkinThickness"],
        data["Insulin"],
        data["BMI"],
        data["DiabetesPedigreeFunction"]
    ]]

    probability = float(diabetes_model.predict_proba(features)[0][1])
    
    raw_probs = diabetes_model.predict_proba(features)
    print("RAW PROBS:", raw_probs)

    probability = float(raw_probs[0][1])


    return {
        "risk": "High Risk" if probability >= 0.5 else "Low Risk",
        "confidence": round(probability, 2)
    }
    
    
