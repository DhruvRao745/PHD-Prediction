"""
SHAP-based explainability for a single prediction.

Each disease model already lives fully-loaded in its own module
(diabetes_model.py, heart_model.py, parkinson_model.py, kidney_model.py) -
this file reuses those same loaded objects instead of loading the
artifacts a second time, so there's still exactly one copy of each model
in memory.

Two different SHAP explainers are used, because the models aren't the
same kind underneath:
  - diabetes/heart/parkinsons are scikit-learn RandomForestClassifiers,
    so shap.TreeExplainer gives fast, exact Shapley values.
  - kidney is a PyTorch network. Instead of hooking into its internals
    (which can break across PyTorch versions), it's treated as a plain
    black-box function - shap.KernelExplainer just calls it like any
    other function and doesn't care what's inside.
"""
import numpy as np
import pandas as pd
import shap
import torch

from app.ml.models.diabetes.diabetes_model import diabetes_model, DIABETES_REQUIRED_FIELDS
from app.ml.models.heart.heart_model import heart_model, HEART_REQUIRED_FIELDS
from app.ml.models.parkinson.parkinson_model import parkinsons_model, PARKINSONS_REQUIRED_FIELDS
from app.ml.models.kidney.kidney_model import (
    model as kidney_model,
    scaler as kidney_scaler,
    imputer as kidney_imputer,
    feature_info as kidney_feature_info,
    label_encoders as kidney_label_encoders,
)

# Building a TreeExplainer/KernelExplainer isn't free - cache one per
# disease instead of rebuilding it on every single request.
_TREE_EXPLAINERS = {}
_KIDNEY_EXPLAINER = None


def _sklearn_pipeline_explanation(disease, pipeline, required_fields, input_data):
    features = pd.DataFrame(
        [[input_data[f] for f in required_fields]],
        columns=required_fields,
    )
    imputed = pd.DataFrame(
        pipeline.named_steps["imputer"].transform(features),
        columns=required_fields,
    )
    scaled = pd.DataFrame(
        pipeline.named_steps["scaler"].transform(imputed),
        columns=required_fields,
    )

    if disease not in _TREE_EXPLAINERS:
        _TREE_EXPLAINERS[disease] = shap.TreeExplainer(pipeline.named_steps["model"])
    explainer = _TREE_EXPLAINERS[disease]

    shap_values = explainer.shap_values(scaled)
    # shape: (1 row, n_features, n_classes) - column 1 is "High Risk".
    contributions = shap_values[0, :, 1]

    return [
        {
            "feature": field,
            "value": input_data[field],
            "contribution": round(float(contributions[i]), 4),
        }
        for i, field in enumerate(required_fields)
    ]


def _kidney_explanation(input_data):
    global _KIDNEY_EXPLAINER

    # Same encode -> order -> impute -> scale steps real_kidney_model()
    # uses, so the explanation matches what the model actually saw.
    input_dict = dict(input_data)
    for col, encoder in kidney_label_encoders.items():
        if col not in input_dict:
            continue
        value = str(input_dict[col]).strip()
        input_dict[col] = encoder.transform([value])[0]

    ordered_cols = kidney_feature_info["all_cols"]
    raw_array = pd.DataFrame(
        [[input_dict[col] for col in ordered_cols]],
        columns=ordered_cols,
    )
    imputed = kidney_imputer.transform(raw_array)
    scaled = kidney_scaler.transform(imputed).astype(np.float32)

    def predict_fn(x):
        with torch.no_grad():
            return kidney_model(torch.tensor(x, dtype=torch.float32)).numpy()

    if _KIDNEY_EXPLAINER is None:
        # All-zero background in the already-scaled space stands in for
        # "an average patient" (the scaler centers real data around 0).
        # Kept tiny so this stays fast enough to run on demand instead of
        # needing to be precomputed ahead of time.
        background = np.zeros((5, len(ordered_cols)), dtype=np.float32)
        _KIDNEY_EXPLAINER = shap.KernelExplainer(predict_fn, background)

    shap_values = _KIDNEY_EXPLAINER.shap_values(scaled, nsamples=100, silent=True)
    contributions = np.array(shap_values).reshape(-1)

    return [
        {
            "feature": col,
            "value": input_data.get(col),
            "contribution": round(float(contributions[i]), 4),
        }
        for i, col in enumerate(ordered_cols)
    ]


def explain_prediction(disease, input_data):
    """Returns a list of {feature, value, contribution} dicts, sorted by
    how much that feature pushed the prediction (either direction),
    strongest first. Positive contribution = pushed toward High Risk,
    negative = pushed toward Low Risk."""
    if not input_data:
        raise ValueError(
            "No stored input data for this prediction - it was made "
            "before explainability was added."
        )

    if disease == "diabetes":
        result = _sklearn_pipeline_explanation(
            "diabetes", diabetes_model, DIABETES_REQUIRED_FIELDS, input_data
        )
    elif disease == "heart":
        result = _sklearn_pipeline_explanation(
            "heart", heart_model, HEART_REQUIRED_FIELDS, input_data
        )
    elif disease == "parkinsons":
        result = _sklearn_pipeline_explanation(
            "parkinsons", parkinsons_model, PARKINSONS_REQUIRED_FIELDS, input_data
        )
    elif disease == "kidney":
        result = _kidney_explanation(input_data)
    else:
        raise ValueError(f"Unknown disease '{disease}'")

    result.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return result
