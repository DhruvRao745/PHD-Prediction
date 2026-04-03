from app.ml.models.diabetes.diabetes_model import real_diabetes_model
from app.ml.models.heart.heart_model import real_heart_model
from app.ml.models.parkinson.parkinson_model import real_parkinsons_model

MODEL_REGISTRY = {
    "diabetes": real_diabetes_model,
    "heart": real_heart_model,
    "parkinsons": real_parkinsons_model
}
