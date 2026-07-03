import os
import pickle

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from imblearn.over_sampling import SMOTE
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app.ml.models.kidney.model import KidneyDiseaseNN


# =====================================================
# Configuration
# =====================================================

DATA_PATH = os.path.join(
    "app", "Data", "Kidney", "kidney_disease.csv"
)

OUTPUT_DIR = os.path.join(
    "app", "ml", "models", "kidney"
)

RANDOM_STATE = 42

os.makedirs(OUTPUT_DIR, exist_ok=True)

torch.manual_seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)


# =====================================================
# Load and clean dataset
# =====================================================

df = pd.read_csv(DATA_PATH)

if "id" in df.columns:
    df = df.drop(columns=["id"])

df.columns = df.columns.str.strip()

# Clean whitespace from every text column
for col in df.select_dtypes(include=["object", "str"]).columns:
    df[col] = df[col].str.strip()

# Replace missing-value symbols
df = df.replace({
    "?": np.nan,
    "": np.nan,
})


# =====================================================
# Clean target
# =====================================================

df["classification"] = (
    df["classification"]
    .astype("string")
    .str.strip()
    .map({
        "ckd": 1,
        "notckd": 0,
    })
)

if df["classification"].isna().any():
    raise ValueError(
        "Unknown or missing values found in classification column."
    )


# =====================================================
# Force medical numeric columns to numeric
# =====================================================

NUMERIC_COLUMNS = [
    "age",
    "bp",
    "sg",
    "al",
    "su",
    "bgr",
    "bu",
    "sc",
    "sod",
    "pot",
    "hemo",
    "pcv",
    "wc",
    "rc",
]

for col in NUMERIC_COLUMNS:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce",
    )


# =====================================================
# Separate features and target
# =====================================================

X = df.drop(columns=["classification"]).copy()
y = df["classification"].astype(int).to_numpy()

categorical_cols = [
    col for col in X.columns
    if col not in NUMERIC_COLUMNS
]

numerical_cols = [
    col for col in X.columns
    if col in NUMERIC_COLUMNS
]

print("Dataset shape:", df.shape)
print("Input features:", X.shape[1])
print("Numerical features:", numerical_cols)
print("Categorical features:", categorical_cols)


# =====================================================
# Train/test split BEFORE fitting preprocessors
# =====================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=RANDOM_STATE,
    stratify=y,
)


# =====================================================
# Encode true categorical columns
# =====================================================

label_encoders = {}

for col in categorical_cols:

    train_mode = X_train[col].mode()

    fill_value = (
        train_mode.iloc[0]
        if not train_mode.empty
        else "unknown"
    )

    X_train[col] = (
        X_train[col]
        .fillna(fill_value)
        .astype(str)
        .str.strip()
    )

    X_test[col] = (
        X_test[col]
        .fillna(fill_value)
        .astype(str)
        .str.strip()
    )

    encoder = LabelEncoder()

    X_train[col] = encoder.fit_transform(
        X_train[col]
    )

    unknown_test_values = set(
        X_test[col].unique()
    ) - set(encoder.classes_)

    if unknown_test_values:
        raise ValueError(
            f"Unseen test values in '{col}': "
            f"{unknown_test_values}"
        )

    X_test[col] = encoder.transform(
        X_test[col]
    )

    label_encoders[col] = encoder


# =====================================================
# Imputation — fit on training data only
# =====================================================

imputer = SimpleImputer(strategy="median")

X_train_imputed = imputer.fit_transform(X_train)
X_test_imputed = imputer.transform(X_test)


# =====================================================
# Scaling — fit on training data only
# =====================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train_imputed
)

X_test_scaled = scaler.transform(
    X_test_imputed
)


# =====================================================
# SMOTE — training data only
# =====================================================

smote = SMOTE(random_state=RANDOM_STATE)

X_train_balanced, y_train_balanced = (
    smote.fit_resample(
        X_train_scaled,
        y_train,
    )
)

print(
    "Training samples after SMOTE:",
    len(X_train_balanced),
)


# =====================================================
# Convert to PyTorch tensors
# =====================================================

X_train_tensor = torch.tensor(
    X_train_balanced,
    dtype=torch.float32,
)

y_train_tensor = torch.tensor(
    y_train_balanced,
    dtype=torch.float32,
).unsqueeze(1)

X_test_tensor = torch.tensor(
    X_test_scaled,
    dtype=torch.float32,
)

y_test_tensor = torch.tensor(
    y_test,
    dtype=torch.float32,
).unsqueeze(1)


# =====================================================
# Create PyTorch model
# =====================================================

input_size = X_train_tensor.shape[1]

model = KidneyDiseaseNN(
    input_size=input_size
)

criterion = nn.BCELoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=0.001,
    weight_decay=1e-4,
)

scheduler = torch.optim.lr_scheduler.StepLR(
    optimizer,
    step_size=50,
    gamma=0.5,
)


# =====================================================
# Train model
# =====================================================

EPOCHS = 200

best_accuracy = 0.0
best_state = None

print("\nTraining PyTorch kidney model...")

for epoch in range(EPOCHS):

    model.train()

    optimizer.zero_grad()

    outputs = model(X_train_tensor)

    loss = criterion(
        outputs,
        y_train_tensor,
    )

    loss.backward()
    optimizer.step()
    scheduler.step()

    if (epoch + 1) % 20 == 0:

        model.eval()

        with torch.no_grad():

            test_probabilities = model(
                X_test_tensor
            )

            test_predictions = (
                test_probabilities >= 0.5
            ).float()

            accuracy = (
                test_predictions == y_test_tensor
            ).float().mean().item()

            auc = roc_auc_score(
                y_test,
                test_probabilities
                .cpu()
                .numpy()
                .flatten(),
            )

        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Loss: {loss.item():.4f} | "
            f"Accuracy: {accuracy * 100:.2f}% | "
            f"AUC: {auc:.4f}"
        )

        if accuracy > best_accuracy:

            best_accuracy = accuracy

            best_state = {
                key: value.detach().cpu().clone()
                for key, value
                in model.state_dict().items()
            }


# =====================================================
# Load best model
# =====================================================

if best_state is None:
    raise RuntimeError(
        "Training finished without saving a best model."
    )

model.load_state_dict(best_state)
model.eval()


# =====================================================
# Final evaluation
# =====================================================

with torch.no_grad():

    probabilities = (
        model(X_test_tensor)
        .cpu()
        .numpy()
        .flatten()
    )

predictions = (
    probabilities >= 0.5
).astype(int)

print("\n" + "=" * 50)
print("FINAL MODEL EVALUATION")
print("=" * 50)

print(
    classification_report(
        y_test,
        predictions,
        target_names=[
            "No CKD",
            "CKD",
        ],
    )
)

print(
    "ROC AUC:",
    round(
        roc_auc_score(
            y_test,
            probabilities,
        ),
        4,
    )
)

print(
    "Best Accuracy:",
    f"{best_accuracy * 100:.2f}%",
)


# =====================================================
# Save PyTorch model
# =====================================================

torch.save(
    model.state_dict(),
    os.path.join(
        OUTPUT_DIR,
        "kidney_model.pth",
    ),
)


# =====================================================
# Save preprocessing artifacts
# =====================================================

with open(
    os.path.join(
        OUTPUT_DIR,
        "scaler.pkl",
    ),
    "wb",
) as f:
    pickle.dump(scaler, f)

with open(
    os.path.join(
        OUTPUT_DIR,
        "imputer.pkl",
    ),
    "wb",
) as f:
    pickle.dump(imputer, f)

with open(
    os.path.join(
        OUTPUT_DIR,
        "label_encoders.pkl",
    ),
    "wb",
) as f:
    pickle.dump(label_encoders, f)


feature_info = {
    "input_size": input_size,
    "numerical_cols": numerical_cols,
    "categorical_cols": categorical_cols,
    "all_cols": list(X.columns),
}

with open(
    os.path.join(
        OUTPUT_DIR,
        "feature_info.pkl",
    ),
    "wb",
) as f:
    pickle.dump(feature_info, f)


print("\nTraining complete.")
print("New PyTorch model and artifacts saved.")