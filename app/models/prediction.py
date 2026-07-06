from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, CheckConstraint, JSON
from datetime import datetime
from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)

    # Renamed from patient_id - this holds whichever account the
    # prediction is about, and that's not always a patient. Doctors can
    # run predictions on themselves too, in which case this is the
    # doctor's own account id.
    account_id = Column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=False,
        index=True
    )

    disease = Column(String, nullable=False)

    # The models only ever actually return "Low Risk" / "High Risk" (see
    # app/ml/models/*/*_model.py) - there's no "Moderate" tier despite
    # what the old comment here implied. If a middle tier gets added
    # later, the constraint below needs updating too.
    risk_level = Column(String)
    probability = Column(Float)        # Raw model output

    input_method = Column(String)      # form / questionnaire / upload

    model_version = Column(String)     # e.g., v1.0

    # The raw feature values submitted for this prediction (age,
    # cholesterol, glucose, etc. - whatever that disease's form
    # collected). Nullable because predictions made before this column
    # existed won't have it. Needed to explain a past prediction after
    # the fact (SHAP needs the exact inputs, not just the result) and to
    # plot real metric values over time, not just the risk label.
    input_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Soft delete: NULL = active. Patients/doctors can soft-delete their
    # own predictions; only admin can restore or permanently hard-delete.
    # Indexed since almost every query filters on "is this still active".
    deleted_at = Column(DateTime, nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(
            "disease IN ('diabetes', 'heart', 'parkinsons', 'kidney')",
            name="ck_predictions_disease",
        ),
        CheckConstraint(
            "risk_level IN ('Low Risk', 'High Risk')",
            name="ck_predictions_risk_level",
        ),
    )