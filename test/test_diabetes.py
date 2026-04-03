from app.ml.models.diabetes.diabetes_model import real_diabetes_model

# Sample realistic input
test_input = {
    "Age": 30,
    "Pregnancies": 5,
    "Glucose": 116,
    "BloodPressure": 74,
    "SkinThickness": 0,
    "Insulin": 0,
    "BMI": 25.6,
    "DiabetesPedigreeFunction": 0.201
}

result = real_diabetes_model(test_input)

print("Prediction Result:")
print(result)
