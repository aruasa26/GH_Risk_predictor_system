🩺Gestational Hypertension (GH) Risk Prediction System

A full-stack predictive healthcare platform that estimates the risk of Gestational Hypertension (GH) in pregnant women using clinical data.
This system integrates machine learning with modern web technologies to assist clinicians in early detection and personalized antenatal care.

🎯 Overview

The GH Risk Prediction System applies a trained deep-learning model called Tabnet to antenatal data to predict whether a patient is at risk of developing gestational hypertension.
It provides a real-time, evidence-based interface for clinicians and patients, combining explainable AI with an efficient digital workflow.

Key Features

Clinical risk prediction — powered by a trained TabNet model

Role-based access — Clinician, Doctor, and Patient interfaces

Automated ANC visit management — next-visit reminders and rescheduling

Persistent prediction storage — every prediction linked to patient history

Explainable output — clear feature-based reasoning for each prediction

Modern UI — fast, responsive dashboards for clinical use

🏗️ Architecture
Technology Stack
Frontend

React (Vite)

Tailwind CSS

Axios API client

React Router + Context API for authentication

Backend

FastAPI (Python)

PostgreSQL database

SQLAlchemy ORM + Alembic migrations

Pydantic for validation

Joblib for model serialization

Machine Learning

PyTorch-TabNet model trained on structured maternal data

Isotonic calibration for probability adjustment

SHAP-based explainability for feature importance

Custom AUC-ROC visualization script (plot_roc.py)

Project Structure
```
GH_Risk_Predictor_System/
├── backend/
│   ├── app/
│   │   ├── gh_predict.py       # ML inference & persistence
│   │   ├── patients.py         # Patient management, resolve & advice
│   │   ├── visits.py           # ANC visit scheduling
│   │   ├── db.py               # Database engine & session factory
│   │   ├── models_risk.py      # ORM models
│   │   └── main.py             # FastAPI entry point
│   └── ml_model/
│       ├── tabnet_model.pkl
│       ├── isotonic_calibrator.pkl
│       ├── feature_order.json
│       ├── threshold.json
│       └── post_rules.json
├── frontend/
│   ├── src/pages/
│   │   ├── ClinicianDashboard.jsx
│   │   └── PatientDashboard.jsx
│   ├── src/components/
│   └── package.json
├── ml_model/
│   ├── X_train.csv / X_test.csv
│   ├── y_train.csv / y_test.csv
│   └── plot_roc.py
└── README.md
```

🚀 Getting Started
Prerequisites

Python 3.10 or later

Node.js 18+

PostgreSQL 15+

Git (for version control)

Installation

Clone the repository

git clone <repo-url>
cd GH_Risk_Predictor_System


Backend setup

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/gh_risk
uvicorn app.main:app --reload


Frontend setup

cd ../frontend
npm install
npm run dev


Access the app at http://localhost:5173

(Optional) Run PostgreSQL in Docker

docker run -d --name gh_postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:15

🔐 Authentication & User Roles
Role	Permissions
Clinician	Enter patient data, generate predictions, record advice
Doctor	View risk results for specific patients
Patient	View personal prediction and next ANC visit

Authentication uses secure email-based or Google Sign-In login, with session management handled by the backend.

🎮 Usage
Clinician Workflow

Search or register a patient.

Enter clinical parameters (Age, BMI, BP, etc.).

Click Predict Risk to generate a result.

Review the risk class (High / Low) and interpretable reasons.

Schedule or update the next ANC visit.

Patient Experience

Log in to view latest GH risk result.

See status and next ANC visit date.

Confirm or reschedule attendance of the scheduled ANC Visit

Review doctor’s advice or notes.

🧠 Machine Learning Model
Model Details

Algorithm: TabNet (PyTorch-TabNet)

Training Data: Two sources were used:

S1 Dataset (Structured clinical data)

Maternal Health Risk Dataset – Mendeley 2022

Target Variable: Gestational Hypertension (0 = No, 1 = Yes)

Production Features (9):

Age, BMI, Systolic BP, Diastolic BP,
Previous Complications, Preexisting Diabetes,
Gestational Diabetes, Mental Health, Heart Rate


Calibration: Isotonic Regression for probability calibration

Explainability: SHAP values for feature importance

Exported Artifacts:

tabnet_model.pkl

isotonic_calibrator.pkl

feature_order.json

threshold.json

post_rules.json (optional)

📈 Model Evaluation — AUC-ROC Visualization

Visualize the Receiver Operating Characteristic curve for your model:

python plot_roc.py \
  --model ./backend/ml_model/tabnet_model.pkl \
  --calibrator ./backend/ml_model/isotonic_calibrator.pkl \
  --features ./backend/ml_model/feature_order.json \
  --x_test ./ml_model/X_test.csv \
  --y_test ./ml_model/y_test.csv \
  --out_png ./ml_model/roc_curve.png \
  --out_csv ./ml_model/roc_points.csv


This script saves:

ml_model/roc_curve.png — ROC plot

ml_model/roc_points.csv — Curve data (FPR, TPR, thresholds)

📡 API Documentation

Interactive docs: http://localhost:8000/docs

Prediction

POST /gh/predict-gh — Generate and save a prediction.

GET /gh/latest/{patient_id} — Retrieve latest prediction.

Patient Endpoints

GET /patients/resolve?q=<email|id|name>

GET /patients/{patient_id}

POST /patients/{id}/advice

Visit Scheduling

GET /visits/gh/me/next-visit?email=<email>

POST /visits/reschedule

🗄️ Database Schema (Overview)
Table	Purpose
users	Stores user credentials and roles
patients	Links to users and medical records
appointments	ANC visit schedules
gh_predictions	Risk results, scores, and reasons
patient_advice	Clinician recommendations & notes
🔧 Configuration
Backend (backend/.env)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/gh_risk
CORS_ORIGINS=http://localhost:5173
SECRET_KEY=your-secret-key

Frontend (frontend/.env)
VITE_API_URL=http://localhost:8000
VITE_APP_NAME="GH Risk Predictor"

🧪 Testing

Backend

pytest -v


Frontend

npm test


API
Swagger UI available at http://localhost:8000/docs

📊 Development Status

✅ Completed

TabNet model training and export

FastAPI prediction API

Patient and Clinician dashboards

Persistent database storage

ANC visit management and advice logging

🚧 Upcoming

Automated email/SMS reminders for upcoming visits

Feature-importance visualization on UI

Clinician analytics dashboard

📈 Future Enhancements

Integration with hospital EHR systems

Mobile-friendly PWA deployment

Predictive alerting for high-risk patients

🧬 Acknowledgements

Developed as a Final Year Project at
Strathmore University — Faculty of Informatics and Computer Science

Supervisor: Mr. Daniel Machanje

📜 License

Released for academic and educational use only.