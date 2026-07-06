from app.models.prediction import Prediction
from app.registry.model_registry import MODEL_REGISTRY


def save_prediction(
    db,
    account_id: int,
    disease: str,
    risk_level: str,
    probability: float,
    input_method: str = "form",
    model_version: str = "v1.0",
    input_data: dict | None = None,
):
    record = Prediction(
        account_id=account_id,
        disease=disease,
        risk_level=risk_level,
        probability=probability,
        input_method=input_method,
        model_version=model_version,
        input_data=input_data,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_risk_summary(db, account_id: int):
    """One row per disease, holding that account's most recent active
    prediction for it (or nulls if they've never run one) - the data
    behind the combined cross-disease risk view. Shared by both the
    patient's own summary and admin's per-patient overview so the two
    can never quietly compute this differently.
    """
    summary = []
    for disease in MODEL_REGISTRY:
        latest = db.query(Prediction).filter(
            Prediction.account_id == account_id,
            Prediction.disease == disease,
            Prediction.deleted_at.is_(None)
        ).order_by(Prediction.created_at.desc()).first()

        summary.append({
            "disease": disease,
            "risk": latest.risk_level if latest else None,
            "confidence": latest.probability if latest else None,
            "date": latest.created_at if latest else None,
        })
    return summary