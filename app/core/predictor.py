from app.registry.model_registry import MODEL_REGISTRY
from app.deps import get_db

def predict(disease, data):

    if disease not in MODEL_REGISTRY:
        return {"error": f"Disease '{disease}' is not supported"}

    if not isinstance(data, dict) or len(data) == 0:
        return {"error": "Invalid or empty data"}

    model_fn = MODEL_REGISTRY[disease]
    result = model_fn(data)

    return {
        "disease": disease,
        "prediction": result
    }
