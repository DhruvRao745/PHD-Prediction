from app.models.prediction import Prediction


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