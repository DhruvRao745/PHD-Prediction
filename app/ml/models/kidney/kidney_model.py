import os
import pickle
import pandas as pd
import numpy as np
import torch

from app.ml.models.kidney.model import KidneyDiseaseNN


# =====================================================
# Paths
# =====================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(CURRENT_DIR, "kidney_model.pth")
SCALER_PATH = os.path.join(CURRENT_DIR, "scaler.pkl")
IMPUTER_PATH = os.path.join(CURRENT_DIR, "imputer.pkl")
FEATURE_INFO_PATH = os.path.join(CURRENT_DIR, "feature_info.pkl")
LABEL_ENCODER_PATH = os.path.join(
    CURRENT_DIR,
    "label_encoders.pkl",
)


# =====================================================
# Load preprocessing artifacts once
# =====================================================

with open(SCALER_PATH, "rb") as f:
    scaler = pickle.load(f)

with open(IMPUTER_PATH, "rb") as f:
    imputer = pickle.load(f)

with open(FEATURE_INFO_PATH, "rb") as f:
    feature_info = pickle.load(f)

with open(LABEL_ENCODER_PATH, "rb") as f:
    label_encoders = pickle.load(f)


# =====================================================
# Load PyTorch model once
# =====================================================

model = KidneyDiseaseNN(
    input_size=feature_info["input_size"]
)

model.load_state_dict(
    torch.load(
        MODEL_PATH,
        map_location=torch.device("cpu"),
    )
)

model.eval()


# =====================================================
# Prediction function
# =====================================================

def real_kidney_model(data):

    input_dict = data.copy()

    # Encode categorical features using the exact
    # LabelEncoder objects fitted during training.
    for col, encoder in label_encoders.items():

        if col not in input_dict:
            continue

        value = str(input_dict[col]).strip()

        try:
            input_dict[col] = encoder.transform(
                [value]
            )[0]

        except ValueError:
            raise ValueError(
                f"Invalid value '{value}' for '{col}'. "
                f"Allowed values: "
                f"{list(encoder.classes_)}"
            )

    # Preserve the exact feature order used in training.
    ordered_cols = feature_info["all_cols"]

    input_array = pd.DataFrame(
    [[input_dict[col] for col in ordered_cols]],
    columns=ordered_cols,
)

    # Apply the same preprocessing used during training.
    input_imputed = imputer.transform(input_array)
    input_scaled = scaler.transform(input_imputed)

    # Convert processed input to a PyTorch tensor.
    input_tensor = torch.tensor(
        input_scaled,
        dtype=torch.float32,
    )

    # Run PyTorch inference.
    with torch.no_grad():
        probability = float(
            model(input_tensor).item()
        )

    return {
        "risk": (
            "High Risk"
            if probability >= 0.5
            else "Low Risk"
        ),
        "confidence": round(probability, 2),
    }