import joblib
import os
import pandas as pd
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

# def validate_diabetes_input(data):
#     missing_fields = [
#         field for field in DIABETES_REQUIRED_FIELDS
#         if field not in data
#     ]

#     if missing_fields:
#         return {
#             "error": f"Missing required fields: {', '.join(missing_fields)}"
#         }
#     # Check numeric type + range
#     errors = validate_numeric(data, DIABETES_RANGES)

#     if errors:
#         return {"error": errors}

#     return None

def validate_diabetes_input(data):

    errors = validate_schema(data, DIABETES_SCHEMA)

    if errors:
        return {"error": errors}

    return None

def real_diabetes_model(data):
    validation_error = validate_diabetes_input(data)
    if validation_error:
        return validation_error

    # Build a DataFrame with the same column names/order the pipeline
    # was trained on (see train_diabetes_model.py).
    features = pd.DataFrame(
        [[data[field] for field in DIABETES_REQUIRED_FIELDS]],
        columns=DIABETES_REQUIRED_FIELDS,
    )

    # diabetes_model is a Pipeline(imputer -> scaler -> model). Calling
    # .predict_proba() on the whole pipeline still warns, because
    # SimpleImputer.transform() returns a plain numpy array internally,
    # so the scaler step loses the column names even when we pass a
    # named DataFrame in. Stepping through manually and re-wrapping each
    # intermediate result keeps the names all the way through.
    imputed = pd.DataFrame(
        diabetes_model.named_steps["imputer"].transform(features),
        columns=DIABETES_REQUIRED_FIELDS,
    )
    scaled = pd.DataFrame(
        diabetes_model.named_steps["scaler"].transform(imputed),
        columns=DIABETES_REQUIRED_FIELDS,
    )
    raw_probs = diabetes_model.named_steps["model"].predict_proba(scaled)
    probability = float(raw_probs[0][1])

    return {
        "risk": "High Risk" if probability >= 0.5 else "Low Risk",
        "confidence": round(probability, 2)
    }
    
    
