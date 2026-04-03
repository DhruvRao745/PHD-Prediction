import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

# Load dataset
df = pd.read_csv("D:\\College\\Projects\\P.H.D. prediction\\app\\Data\\Parkinson\\parkinsons.csv")

X = df.drop(["status", "name"], axis=1)
y = df["status"]

# Replace impossible zeros with NaN (if any)
# (In Parkinson's dataset, there might not be such features, but this is a common step in medical datasets)
# cols = ["some_feature"]
# for col in cols:
#     df[col] = df[col].replace(0, np.nan)

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
# joblib.dump(pipeline, "app/artifacts/parkinsons_model.joblib")
# print("✅ Parkinson's model trained and saved")

input_data = [[174.688,240.005,74.287,0.0136,0.00008,0.00624,0.00564,0.01873,0.02308,0.256,0.01268,0.01365,0.01667,0.03804,0.10715,17.883,0.407567,0.655683,-6.787197,0.158453,2.679772,0.131728]]
prediction = pipeline.predict(input_data)   
if prediction[0] == 1:
    print("The model predicts that the patient HAS Parkinson's disease.")   
else:
    print("The model predicts that the patient does NOT have Parkinson's disease.")  
