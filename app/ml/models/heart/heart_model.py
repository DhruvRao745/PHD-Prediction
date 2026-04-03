import os
import joblib
from app.utils.validation import check_missing_fields, check_numeric_fields, validate_schema
from app.utils.schemas import HEART_SCHEMA


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

APP_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)

MODEL_PATH = os.path.join(APP_DIR, "artifacts", "heart_model.joblib")

heart_model = joblib.load(MODEL_PATH)


HEART_REQUIRED_FIELDS = [
    "age","sex","cp","trestbps","chol","fbs",
    "restecg","thalach","exang","oldpeak",
    "slope","ca","thal"
]


# def validate_heart_input(data):
#     missing_fields = [
#         field for field in HEART_REQUIRED_FIELDS 
#         if field not in data
#     ]
    
#     if missing_fields:
#         return {"error": f"Missing fields: {', '.join(missing_fields)}"}
#     return None

def validate_heart_input(data):

    errors = validate_schema(data, HEART_SCHEMA)

    if errors:
        return {"error": errors}

    return None



def real_heart_model(data):
    validation_error = validate_heart_input(data)
    if validation_error:
        return validation_error

    features = [[
        data["age"], data["sex"], data["cp"],
        data["trestbps"], data["chol"], data["fbs"],
        data["restecg"], data["thalach"], data["exang"],
        data["oldpeak"], data["slope"], data["ca"],
        data["thal"]
    ]]

    probability = float(heart_model.predict_proba(features)[0][1])
    
    raw_probs = heart_model.predict_proba(features)
    print("RAW PROBS:", raw_probs)

    probability = float(raw_probs[0][1])

    return {
        "risk": "High Risk" if probability >= 0.5 else "Low Risk",
        "confidence": round(probability, 2)
    }
