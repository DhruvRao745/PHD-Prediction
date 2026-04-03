import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

# Load data
df = pd.read_csv("D:\\College\\Projects\\P.H.D. prediction\\app\\Data\\Diabetes\\diabetes.csv")

X = df.drop("Outcome", axis=1)
y = df["Outcome"]

# Replace impossible zeros (these features cannot be zero)
cols = ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]
X[cols] = X[cols].replace(0, np.nan)

# Pipeline
pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("model", RandomForestClassifier(n_estimators=200))
])

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

pipeline.fit(X_train, y_train)

# Evaluation
y_pred = pipeline.predict(X_test)

print(classification_report(y_test, y_pred))
print("ROC AUC:", roc_auc_score(y_test, pipeline.predict_proba(X_test)[:,1]))

# Cross-validation
cv_score = cross_val_score(pipeline, X, y, cv=5).mean()
print("CV Score:", cv_score)

# Save model
# joblib.dump(pipeline, "app/artifacts/diabetes_model.joblib")

# print("Diabetes model trained and saved to app/artifacts/diabetes_model.joblib")


input_data = [[36,3,187,70,22,200,36.4,0.408]]

prediction = pipeline.predict(input_data)

# print(f"Predicted outcome for input data {input_data}: {prediction[0]}")

if prediction[0] == 1:
    print("The model predicts that the patient HAS diabetes.")
else:
    print("The model predicts that the patient does NOT have diabetes.")
