import os
import joblib
import pandas as pd
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

    # Named DataFrame matching training column order (train_heart_model.py).
    features = pd.DataFrame(
        [[data[field] for field in HEART_REQUIRED_FIELDS]],
        columns=HEART_REQUIRED_FIELDS,
    )

    # Step through the pipeline manually instead of calling
    # heart_model.predict_proba() directly - SimpleImputer.transform()
    # drops back to a plain numpy array internally, so the scaler step
    # would still warn even with a named DataFrame as the initial input.
    imputed = pd.DataFrame(
        heart_model.named_steps["imputer"].transform(features),
        columns=HEART_REQUIRED_FIELDS,
    )
    scaled = pd.DataFrame(
        heart_model.named_steps["scaler"].transform(imputed),
        columns=HEART_REQUIRED_FIELDS,
    )
    raw_probs = heart_model.named_steps["model"].predict_proba(scaled)
    probability = float(raw_probs[0][1])

    return {
        "risk": "High Risk" if probability >= 0.5 else "Low Risk",
        "confidence": round(probability, 2)
    }
