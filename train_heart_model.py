import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

# Load data
df = pd.read_csv("D:\\College\\Projects\\P.H.D. prediction\\app\\Data\\Heart\\heart.csv")

X = df.drop("target", axis=1)
y = df["target"]

# Replace impossible zeros (these features cannot be zero)
cols = ["trestbps", "chol", "thalach", "oldpeak"]

for col in cols:
    df[col] = df[col].replace(0, np.nan)

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

# Evaluate
y_pred = pipeline.predict(X_test)

print(classification_report(y_test, y_pred))
print("ROC AUC:", roc_auc_score(y_test, pipeline.predict_proba(X_test)[:,1]))   

# Cross-validation
cv_score = cross_val_score(pipeline, X, y, cv=5).mean()
print("CV Score:", cv_score)

# Save model
# joblib.dump(pipeline, "app/artifacts/heart_model.joblib")
# print("✅ Heart model trained and saved")

input_data = [[56,1,2,130,256,1,0,142,1,0.6,1,1,1]]
prediction = pipeline.predict(input_data)
if prediction[0] == 1:
    print("The model predicts that the patient HAS heart disease.")
else:    
    print("The model predicts that the patient does NOT have heart disease.")  