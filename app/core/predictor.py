from app.registry.model_registry import MODEL_REGISTRY

from app.utils.schemas import (
    KIDNEY_NUMERIC_SCHEMA,
    KIDNEY_CATEGORICAL_SCHEMA,
)

from app.utils.validation import validate_kidney_schema


def predict(disease, data):

    disease = disease.strip().lower()

    if disease not in MODEL_REGISTRY:
        return {
            "error": f"Disease '{disease}' is not supported"
        }

    if not isinstance(data, dict) or len(data) == 0:
        return {
            "error": "Invalid or empty data"
        }

    # Kidney-specific mixed validation
    if disease == "kidney":

        errors = validate_kidney_schema(
            data,
            KIDNEY_NUMERIC_SCHEMA,
            KIDNEY_CATEGORICAL_SCHEMA,
        )

        if errors:
            return {
                "error": "Validation failed",
                "details": errors,
            }

        # Normalize categorical values
        for field in KIDNEY_CATEGORICAL_SCHEMA:
            data[field] = data[field].strip().lower()

    model_fn = MODEL_REGISTRY[disease]

    try:
        result = model_fn(data)

    except Exception as exc:
        return {
            "error": "Prediction failed",
            "details": str(exc),
        }

    return {
        "disease": disease,
        "prediction": result,
    }