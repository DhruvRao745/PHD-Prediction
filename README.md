# Multiple Disease Prediction System

A full-stack ML platform for predicting risk of four diseases - diabetes, heart disease, Parkinson's, and chronic kidney disease (CKD) - with a FastAPI backend, a React frontend, JWT authentication, PostgreSQL persistence, and role-based access for patients and doctors.

This is an educational/portfolio ML engineering project. It is **not** a clinically validated diagnostic tool - see [Model Results](#model-results) for details.

## Features

- JWT authentication with patient/doctor roles
- Risk prediction for 4 diseases via a single `/predict` endpoint
- Diabetes, heart disease, and Parkinson's use scikit-learn (`RandomForestClassifier`) pipelines
- CKD prediction uses a genuine **PyTorch** neural network, with leakage-safe preprocessing (train/test split before SMOTE and before fitting the imputer/scaler)
- Patient dashboard: profile, run predictions, view history
- Doctor dashboard: profile, assign patients, view each patient's prediction history, and check their own risk too
- Bulk-fill on every prediction form: paste JSON, a CSV row, or `field: value` lines (or upload a file) instead of typing 20+ fields by hand
- Auto-filled/locked age, sex, and pregnancy fields sourced from the patient's own profile, so predictions can't be submitted with inconsistent demographic data
- Smart duplicate-prediction filtering (same patient/disease/probability within an hour is not re-saved)

## Tech Stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL (via Docker), scikit-learn, PyTorch, pandas, imbalanced-learn (SMOTE), python-jose (JWT), passlib (bcrypt)

**Frontend:** React (Vite), react-router-dom - plain fetch-based API client, no external UI framework yet (a visual redesign is planned separately)

## Project Structure

```
app/
  auth/            # register/login/me routes, JWT + password hashing
  core/predictor.py  # central dispatch: validates input, calls the right model, normalizes errors
  ml/models/       # one folder per disease: model code + trained artifacts
  models/          # SQLAlchemy tables (accounts, profiles, predictions, doctor-patient links)
  registry/        # MODEL_REGISTRY mapping disease name -> prediction function
  services/        # prediction persistence + duplicate check
  utils/           # per-disease validation schemas
  Data/            # training CSVs
  artifacts/       # trained scikit-learn models (.joblib)
frontend/
  src/api/         # fetch wrapper (base URL, auth header, error parsing)
  src/auth/        # AuthContext + ProtectedRoute
  src/config/      # field definitions for all 4 prediction forms
  src/pages/       # routed pages (dashboards, profile forms, predict, history)
  src/components/  # shared PredictionForm component
train_*.py          # training scripts (diabetes, heart, parkinsons, kidney)
```

## Setup

### Backend

Requires Python 3.11 (not 3.14 - some ML packages had build issues on it).

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Start PostgreSQL (Docker Desktop must be running):

```
docker compose up -d   # or however your Postgres container is started
python create_tables.py
```

Run the API:

```
python run_server.py
```

Swagger docs: http://127.0.0.1:8000/docs

### Frontend

```
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173, configured via `frontend/.env` (`VITE_API_BASE_URL`, see `.env.example`) to talk to the backend at `http://127.0.0.1:8000`. CORS is already enabled on the backend for this origin.

## API Overview

All endpoints except `/auth/register` and `/auth/login` require `Authorization: Bearer <token>`.

| Endpoint | Method | Description |
|---|---|---|
| `/auth/register` | POST | Create an account (JSON body: `username`, `password`, `role`) |
| `/auth/login` | POST | Get a JWT (form-encoded: `username`, `password`) |
| `/auth/me` | GET | Current user's `id`/`role`/`username` |
| `/predict` | POST | Run a prediction (JSON body: `disease`, `data`) |
| `/history` | GET | Caller's own prediction history, optional `?disease=` filter |
| `/dashboard/patient` | GET | Patient profile + recent predictions (patient only) |
| `/dashboard/doctor` | GET | Doctor profile + assigned patients' predictions (doctor only) |
| `/doctor/assign-patient` | POST | Assign a patient by numeric ID (doctor only, query param `patient_id`) |
| `/profile/patient` | POST | Create/overwrite patient profile (query params, not JSON body) |
| `/profile/doctor` | POST | Create/overwrite doctor profile (query params, not JSON body) |

### Example: prediction request

```json
POST /predict
{
  "disease": "kidney",
  "data": {
    "age": 48, "bp": 80, "sg": 1.02, "al": 1, "su": 0,
    "rbc": "normal", "pc": "normal", "pcc": "notpresent", "ba": "notpresent",
    "bgr": 121, "bu": 36, "sc": 1.2, "sod": 135, "pot": 4.5, "hemo": 15.4,
    "pcv": 44, "wc": 7800, "rc": 5.2,
    "htn": "no", "dm": "no", "cad": "no", "appet": "good", "pe": "no", "ane": "no"
  }
}
```

```json
{
  "status": "success",
  "data": { "risk": "Low Risk", "confidence": 0.13 }
}
```

Validation failures return `400` with `{"detail": {"error": "Validation failed", "details": [...]}}`.

## Model Results

**CKD (PyTorch):** trained on 400 rows (80 held-out test samples) after correcting two pipeline bugs - dirty numeric columns (`pcv`, `wc`, `rc`) that were being label-encoded as categories instead of parsed as numbers, and SMOTE being applied before the train/test split (data leakage). After fixes: 98.75% test accuracy, ROC AUC 1.0, precision/recall of 0.97-1.00 across both classes. These numbers come from a single 80-sample test split on a small (400-row) public dataset - they demonstrate a correct, leakage-safe ML pipeline, not clinical reliability.

**Diabetes / Heart / Parkinson's (scikit-learn `RandomForestClassifier`):** each trained via a 5-fold cross-validated `Pipeline(imputer -> scaler -> model)` on its respective public dataset (Pima Diabetes, UCI Heart Disease, UCI Parkinson's). Exact accuracy/ROC-AUC figures aren't recorded anywhere in this repo (only printed to console during training and not saved) - re-run the relevant `train_*.py` script to reproduce them before quoting numbers anywhere.

**This project should not be described as a diagnostic tool or clinically validated system.**

## Known Limitations / Next Steps

- Profile update endpoints (`/profile/patient`, `/profile/doctor`) always require all fields and fully overwrite the row - no partial update yet, and the frontend doesn't pre-fill existing values before editing
- No patient search for doctors - assigning a patient requires knowing their raw numeric account ID
- No delete functionality anywhere yet (accounts, profiles, or predictions)
- `requirements.txt` is broader than the project's direct dependencies (originated from an environment freeze)
- JWT auth goes through `python-jose`, which transitively depends on `ecdsa` (flagged in a past PR review) - a move to PyJWT + cryptography is planned separately
- Model artifacts load at import time - a missing/corrupt artifact currently prevents the whole API from starting
- Only a handful of automated tests exist (`test/`); most testing so far has been manual via Swagger/Postman and the frontend
- Not containerized or deployed anywhere yet
- Frontend styling is intentionally minimal - a visual redesign is planned via Lovable/Stitch

## Status

Backend: 4 working disease models (3 scikit-learn + 1 PyTorch), auth, PostgreSQL persistence, doctor/patient roles.
Frontend: React app covering auth, both dashboards, all 4 prediction forms, and history - functional, not yet restyled.
Not yet built: partial profile updates, delete operations, patient search, deployment.
