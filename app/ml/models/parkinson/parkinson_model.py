import os
import joblib
import pandas as pd
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

    # Named DataFrame matching training column order (train_parkinson_model.py).
    features = pd.DataFrame(
        [[data[f] for f in PARKINSONS_REQUIRED_FIELDS]],
        columns=PARKINSONS_REQUIRED_FIELDS,
    )

    # Step through the pipeline manually instead of calling
    # parkinsons_model.predict_proba() directly - SimpleImputer.transform()
    # drops back to a plain numpy array internally, so the scaler step
    # would still warn even with a named DataFrame as the initial input.
    imputed = pd.DataFrame(
        parkinsons_model.named_steps["imputer"].transform(features),
        columns=PARKINSONS_REQUIRED_FIELDS,
    )
    scaled = pd.DataFrame(
        parkinsons_model.named_steps["scaler"].transform(imputed),
        columns=PARKINSONS_REQUIRED_FIELDS,
    )
    raw_probs = parkinsons_model.named_steps["model"].predict_proba(scaled)
    probability = float(raw_probs[0][1])

    return {
        "risk": "High Risk" if probability >= 0.5 else "Low Risk",
        "confidence": round(probability, 2)
    }
