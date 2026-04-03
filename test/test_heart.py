from app.ml.models.heart.heart_model import real_heart_model
# Sample realistic input

test_input = {
  "disease": "heart",
  "data": {
    "age": 44,
    "sex": 1,
    "cp": 2,
    "trestbps": 130,
    "chol": 233,
    "fbs": 0,
    "restecg": 1,
    "thalach": 179,
    "exang": 1,
    "oldpeak": 0.4,
    "slope": 2,
    "ca": 0,
    "thal": 2
  }
}

result = real_heart_model(test_input["data"])
print("Prediction Result:")
print(result)
