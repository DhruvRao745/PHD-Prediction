# ================================
# 🩸 Diabetes Schema
# ================================
DIABETES_SCHEMA = {
    "Age": (0, 120),
    "Pregnancies": (0, 20),
    "Glucose": (0, 300),
    "BloodPressure": (0, 200),
    "SkinThickness": (0, 100),
    "Insulin": (0, 900),
    "BMI": (0, 70),
    "DiabetesPedigreeFunction": (0, 3)
}


# ================================
# ❤️ Heart Disease Schema
# ================================
HEART_SCHEMA = {
    "age": (0, 120),
    "sex": (0, 1),
    "cp": (0, 3),
    "trestbps": (0, 250),
    "chol": (0, 600),
    "fbs": (0, 1),
    "restecg": (0, 2),
    "thalach": (0, 250),
    "exang": (0, 1),
    "oldpeak": (0, 10),
    "slope": (0, 2),
    "ca": (0, 4),
    "thal": (0, 3)
}


# ================================
# 🧠 Parkinson’s Schema
# ================================
PARKINSONS_SCHEMA = {
    "MDVP:Fo(Hz)": (0, 500),
    "MDVP:Fhi(Hz)": (0, 600),
    "MDVP:Flo(Hz)": (0, 400),
    "MDVP:Jitter(%)": (0, 1),
    "MDVP:Jitter(Abs)": (0, 1),
    "MDVP:RAP": (0, 1),
    "MDVP:PPQ": (0, 1),
    "Jitter:DDP": (0, 1),
    "MDVP:Shimmer": (0, 1),
    "MDVP:Shimmer(dB)": (0, 5),
    "Shimmer:APQ3": (0, 1),
    "Shimmer:APQ5": (0, 1),
    "MDVP:APQ": (0, 1),
    "Shimmer:DDA": (0, 1),
    "NHR": (0, 1),
    "HNR": (0, 50),
    "RPDE": (0, 1),
    "DFA": (0, 1),
    "spread1": (-10, 10),
    "spread2": (-10, 10),
    "D2": (0, 10),
    "PPE": (0, 1)
}
