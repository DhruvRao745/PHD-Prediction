import os
import joblib
from app.utils.validation import check_missing_fields, check_numeric_fields, validate_schema
from app.utils.schemas import PARKINSONS_SCHEMA


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

APP_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(CURRENT_DIR)
    )
)

MODEL_PATH = os.path.join(APP_DIR, "artifacts", "parkinsons_model.joblib")

parkinsons_model = joblib.load(MODEL_PATH)


# IMPORTANT:
# Replace with actual column names from your dataset
PARKINSONS_REQUIRED_FIELDS = [
    "MDVP:Fo(Hz)", "MDVP:Fhi(Hz)", "MDVP:Flo(Hz)",
    "MDVP:Jitter(%)", "MDVP:Jitter(Abs)",
    "MDVP:RAP", "MDVP:PPQ", "Jitter:DDP",
    "MDVP:Shimmer", "MDVP:Shimmer(dB)",
    "Shimmer:APQ3", "Shimmer:APQ5",
    "MDVP:APQ", "Shimmer:DDA",
    "NHR", "HNR",
    "RPDE", "DFA",
    "spread1", "spread2",
    "D2", "PPE"
]


# def validate_parkinsons_input(data):
#     missing_fields = [
#         f for f in PARKINSONS_REQUIRED_FIELDS 
#         if f not in data
#     ]
    
#     if missing_fields:
#         return {"error": f"Missing fields: {', '.join(missing_fields)}"}
#     return None

def validate_parkinsons_input(data):

    errors = validate_schema(data, PARKINSONS_SCHEMA)

    if errors:
        return {"error": errors}

    return None



def real_parkinsons_model(data):
    validation_error = validate_parkinsons_input(data)
    if validation_error:
        return validation_error

    features = [[data[f] for f in PARKINSONS_REQUIRED_FIELDS]]

    probability = float(parkinsons_model.predict_proba(features)[0][1])
    
    raw_probs = parkinsons_model.predict_proba(features)
    print("RAW PROBS:", raw_probs)
    
    probability = float(raw_probs[0][1])

    return {
        "risk": "High Risk" if probability >= 0.5 else "Low Risk",
        "confidence": round(probability, 2)
    }
