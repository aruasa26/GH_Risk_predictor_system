# Gestational Hypertension (GH) Risk Prediction System

**A full-stack predictive healthcare platform that estimates the risk of Gestational Hypertension (GH) in pregnant women using clinical data.**

This system integrates deep learning (TabNet) with modern web technologies to assist clinicians in early detection and personalized antenatal care (ANC) management.

---

##  Overview

The GH Risk Prediction System applies a trained **PyTorch-TabNet** model to antenatal data to predict whether a patient is at risk of developing gestational hypertension. It shifts care from reactive to predictive, providing a real-time, evidence-based interface for clinicians and patients that combines explainable AI with an efficient digital workflow.

## Key Features

* **Clinical Risk Prediction:** Real-time inference powered by a trained TabNet deep learning model.
* **Role-Based Access Control:** Dedicated interfaces for **Clinicians** (Input/Manage), **Doctors** (Oversight), and **Patients** (View).
* **ANC Management:** ANC next-visit scheduling and rescheduling capabilities.
* **Persistent History:** Every prediction is stored and linked to the patient's medical history for longitudinal tracking.
* **Explainable AI (XAI):** Clear, feature-based reasoning (using SHAP values) for every prediction to aid clinical trust.
* **⚡ Modern UI:** Fast, responsive dashboards built with React and Tailwind CSS.

---

##  Architecture & Technology Stack

### Frontend
* **Framework:** React (Vite)
* **Styling:** Tailwind CSS
* **State/Auth:** React Router + Context API
* **Networking:** Axios

### Backend
* **Framework:** FastAPI (Python)
* **Database:** PostgreSQL 15+
* **ORM:** SQLAlchemy + Alembic (Migrations)
* **Validation:** Pydantic
* **Serialization:** Joblib

### Machine Learning
* **Model:** PyTorch-TabNet (Deep Learning for Tabular Data)
* **Calibration:** Isotonic Regression (for probability adjustment)
* **Explainability:** SHAP (Shapley Additive Explanations)
* **Visualization:** Matplotlib/Seaborn (Custom ROC scripts)

---

## 📂 Project Structure
```
GH_Risk_Predictor_System/
├── backend/
│   ├── app/
│   │   ├── gh_predict.py       # ML inference logic & persistence
│   │   ├── patients.py         # Patient management endpoints
│   │   ├── visits.py           # ANC visit scheduling logic
│   │   ├── db.py               # Database engine & session factory
│   │   ├── models_risk.py      # SQLAlchemy ORM models
│   │   └── main.py             # FastAPI entry point
│   └── ml_model/
│       ├── tabnet_model.pkl    # Trained Model
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
├── ml_model/                 # Training scripts & data
│   ├── X_train.csv / X_test.csv
│   ├── y_train.csv / y_test.csv
│   └── plot_roc.py
└── README.md
```

---

## Machine Learning Model Details

### Model Specs

* **Algorithm:** TabNet (PyTorch-TabNet)
* **Target Variable:** Gestational Hypertension (0 = No, 1 = Yes)
* **Calibration:** Isotonic Regression applied to raw logits for accurate probability scoring.

### Data Sources

The model was trained on a harmonized dataset from:

* **S1 Dataset** (Structured clinical data from Kathmandu Hospital).
* **Maternal Health Risk Dataset** (Mendeley Data 2022).

### Production Features (9 Core Inputs)

The model uses the following 9 features for inference:

1. Age
2. BMI
3. Systolic BP
4. Diastolic BP
5. Previous Complications
6. Preexisting Diabetes
7. Gestational Diabetes
8. Mental Health History
9. Heart Rate

### Evaluation (AUC-ROC)

To visualize the performance of the model on test data:
```bash
python plot_roc.py \
  --model ./backend/ml_model/tabnet_model.pkl \
  --calibrator ./backend/ml_model/isotonic_calibrator.pkl \
  --features ./backend/ml_model/feature_order.json \
  --x_test ./ml_model/X_test.csv \
  --y_test ./ml_model/y_test.csv \
  --out_png ./ml_model/roc_curve.png \
  --out_csv ./ml_model/roc_points.csv
```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* Node.js 18+
* PostgreSQL 15+
* Git

### 1. Installation
```bash
git clone <your-repo-url>
cd GH_Risk_Predictor_System
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Configure DB Connection
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/gh_risk

# Run Server
uvicorn app.main:app --reload
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

Access the app at `http://localhost:5173`

### 4. (Optional) Run Database via Docker
```bash
docker run -d --name gh_postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 postgres:15
```

---

##  Authentication & User Roles

Authentication is handled via secure email login or Google Sign-In.

| Role | Permissions |
|------|-------------|
| **Clinician** | Register patients, input clinical data, generate predictions, record advice. |
| **Doctor** | View high-level risk results and patient history. |
| **Patient** | View personal prediction results and next scheduled ANC visit. |

---

## 🎮 Usage Guide

### Clinician Workflow

1. **Search/Register:** Locate patient via email or ID.
2. **Input Data:** Enter the 9 clinical parameters (BP, BMI, etc.).
3. **Predict:** Click "Predict Risk".
4. **Review:** See High/Low classification and SHAP-based reasons.
5. **Schedule:** System suggests next ANC visit date; Clinician confirms.

### Patient Workflow

1. **Login:** Access personal dashboard.
2. **View Status:** See latest risk result.
3. **ANC Visit:** Check date of next appointment.
4. **Advice:** Read notes left by the doctor.

---

## API Documentation

Interactive Swagger UI is available at `http://localhost:8000/docs` when backend is running.

### Key Endpoints

* `POST /gh/predict-gh` — Generate prediction & save to DB.
* `GET /gh/latest/{patient_id}` — Get most recent risk assessment.
* `GET /patients/resolve` — Search patient by email/ID.
* `POST /visits/reschedule` — Modify ANC appointment.

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Auth credentials, roles, email. |
| `patients` | Demographics, links to user accounts. |
| `gh_predictions` | ML results, probabilities, input snapshots. |
| `appointments` | ANC visit dates and status. |
| `patient_advice` | Clinical notes from doctors. |

---

## Configuration

### Backend (`backend/.env`)
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/gh_risk
CORS_ORIGINS=http://localhost:5173
SECRET_KEY=your-secret-key-here
```

### Frontend (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME="GH Risk Predictor"
```

---

##  Testing

### Backend
```bash
pytest -v
```

### Frontend
```bash
npm test
```

### API

Swagger UI available at `http://localhost:8000/docs`

---

## Development Status

* **Completed:** TabNet training, FastAPI backend, React Dashboards, DB Persistence, ANC Scheduling.
* **In Progress:** Automated Email/SMS reminders.
* **Future:** EHR Integration (HL7/FHIR), PWA Mobile deployment.

---

## 🧬 Acknowledgements

Developed as a **Final Year Project** at **Strathmore University** — Faculty of Informatics and Computer Science.

**Supervisor:** Mr. Daniel Machanje

---

## License

Released for academic and educational use only.