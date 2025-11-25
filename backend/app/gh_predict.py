# backend/app/gh_predict.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import joblib, json, os, numpy as np, logging, traceback

from .db import get_db, engine

router = APIRouter()

# -------------------------------------------------
#                MODEL / ARTIFACTS
# -------------------------------------------------
MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml_model"))
POSSIBLE_MODEL_FILES = [
    os.path.join(MODEL_DIR, "tabnet_model.joblib"),
    os.path.join(MODEL_DIR, "tabnet_model.pkl"),
]
CAL_PATH   = os.path.join(MODEL_DIR, "isotonic_calibrator.pkl")
THR_JSON   = os.path.join(MODEL_DIR, "threshold.json")
FEAT_JSON  = os.path.join(MODEL_DIR, "feature_order.json")
RULES_JSON = os.path.join(MODEL_DIR, "post_rules.json")

_model = None
for p in POSSIBLE_MODEL_FILES:
    if os.path.isfile(p):
        _model = joblib.load(p)
        break
if _model is None:
    raise RuntimeError(f"TabNet model not found in {POSSIBLE_MODEL_FILES}. Train/export first.")

_iso = joblib.load(CAL_PATH) if os.path.isfile(CAL_PATH) else None

_threshold = 0.5
if os.path.isfile(THR_JSON):
    try:
        _threshold = float(json.load(open(THR_JSON))["threshold"])
    except Exception:
        _threshold = 0.5
if _threshold < 0.05 or _threshold > 0.95:
    logging.getLogger("uvicorn.error").warning(f"[GH] Threshold {_threshold} looks suspicious; clamping to 0.5")
    _threshold = 0.5

# Feature order from training export
if not os.path.isfile(FEAT_JSON):
    raise RuntimeError("feature_order.json missing. Export it during training.")
_features = list(json.load(open(FEAT_JSON)))

# Production 9 input features
EXPECTED_9 = [
    "Age",
    "BMI",
    "Systolic BP",
    "Diastolic BP",
    "Previous Complications",
    "Preexisting Diabetes",
    "Gestational Diabetes",
    "Mental Health",
    "Heart Rate",
]

_feat_index = {name: _features.index(name) for name in _features}
_missing_crit = [f for f in EXPECTED_9 if f not in _feat_index]
if _missing_crit:
    raise RuntimeError(f"Trained features missing critical fields: {_missing_crit}")

_post_rules = {}
if os.path.isfile(RULES_JSON):
    try:
        _post_rules = json.load(open(RULES_JSON))
    except Exception:
        _post_rules = {}

# -------------------------------------------------
#                DB PERSISTENCE
# -------------------------------------------------
# Ensure table exists
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS gh_predictions (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            risk_class TEXT NOT NULL,
            risk_score DOUBLE PRECISION NOT NULL,
            priority BOOLEAN NOT NULL DEFAULT FALSE,
            reasons JSONB,
            threshold_used DOUBLE PRECISION,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))
    conn.commit()

def save_prediction(db: Session, patient_id: int, risk_class: str,
                    risk_score: float, priority: bool, reasons: Optional[List[str]],
                    threshold_used: float):
    try:
        db.execute(text("""
            INSERT INTO gh_predictions (patient_id, risk_class, risk_score, priority, reasons, threshold_used)
            VALUES (:pid, :rc, :rs, :pr, CAST(:reasons AS JSONB), :thr)
        """), {
            "pid": patient_id,
            "rc": risk_class,
            "rs": float(risk_score),
            "pr": bool(priority),
            "reasons": json.dumps(reasons or []),
            "thr": float(threshold_used)
        })
        db.commit()
        logging.getLogger("uvicorn.error").info(f"[GH] saved prediction pid={patient_id}, rc={risk_class}, score={risk_score}")
    except Exception as e:
        db.rollback()
        logging.getLogger("uvicorn.error").error(f"[GH] save failed: {e}")
        traceback.print_exc()

def latest_prediction(db: Session, patient_id: int):
    row = db.execute(text("""
        SELECT id, patient_id, risk_class, risk_score, priority,
               COALESCE(reasons, '[]'::jsonb) AS reasons,
               COALESCE(threshold_used, 0.5) AS threshold_used,
               created_at
        FROM gh_predictions
        WHERE patient_id = :pid
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """), {"pid": patient_id}).mappings().first()
    return row

# -------------------------------------------------
#                 SCHEMAS / API
# -------------------------------------------------
class PredictIn(BaseModel):
    patient_id: Optional[int] = None
    age: int = Field(..., ge=10, le=60)
    bmi: float = Field(..., ge=10, le=80)
    systolic_bp: int = Field(..., ge=60, le=250)
    diastolic_bp: int = Field(..., ge=40, le=150)
    previous_complications: int = Field(..., ge=0, le=1)
    preexisting_diabetes: int = Field(..., ge=0, le=1)
    gestational_diabetes: int = Field(..., ge=0, le=1)
    mental_health: int = Field(..., ge=0, le=1)
    heart_rate: int = Field(..., ge=40, le=220)

    @validator(
        "previous_complications",
        "preexisting_diabetes",
        "gestational_diabetes",
        "mental_health"
    )
    def _bin01(cls, v): return int(bool(v))

class PredictOut(BaseModel):
    risk_score: float
    risk_class: str
    threshold_used: float
    priority: Optional[bool] = False
    reasons: Optional[List[str]] = []
    created_at: Optional[str] = None

# -------------------------------------------------
#             HELPER FUNCTIONS
# -------------------------------------------------
def _vector_from_payload(p: PredictIn):
    row = np.zeros((1, len(_features)), dtype=np.float32)
    values = {
        "Age": float(p.age),
        "BMI": float(p.bmi),
        "Systolic BP": float(p.systolic_bp),
        "Diastolic BP": float(p.diastolic_bp),
        "Previous Complications": float(p.previous_complications),
        "Preexisting Diabetes": float(p.preexisting_diabetes),
        "Gestational Diabetes": float(p.gestational_diabetes),
        "Mental Health": float(p.mental_health),
        "Heart Rate": float(p.heart_rate),
    }
    for name, val in values.items():
        idx = _feat_index[name]
        row[0, idx] = val
    return row

def _priority_reasons(p: PredictIn) -> (bool, List[str]):
    reasons = []
    if p.systolic_bp >= 140: reasons.append(f"SBP ≥ 140 ({p.systolic_bp})")
    if p.diastolic_bp >= 90: reasons.append(f"DBP ≥ 90 ({p.diastolic_bp})")
    if p.systolic_bp >= 130 and p.diastolic_bp >= 85:
        reasons.append(f"SBP ≥ 130 & DBP ≥ 85 ({p.systolic_bp}/{p.diastolic_bp})")
    if p.bmi >= 35: reasons.append(f"BMI ≥ 35 ({p.bmi})")
    if p.age < 18 or p.age > 40: reasons.append(f"Age high-risk ({p.age})")
    if p.previous_complications: reasons.append("Previous complications")
    if p.preexisting_diabetes:  reasons.append("Pre-existing diabetes")
    if p.gestational_diabetes:  reasons.append("Gestational diabetes")
    if p.mental_health:         reasons.append("Diagnosed mental health condition")
    return (len(reasons) > 0, reasons)

# -------------------------------------------------
#             PREDICT ENDPOINT
# -------------------------------------------------
@router.post("/gh/predict-gh", response_model=PredictOut)
def predict(payload: PredictIn, db: Session = Depends(get_db)):
    X = _vector_from_payload(payload)

    try:
        proba = _model.predict_proba(X)[0]
        pos_idx = 1 if hasattr(_model, "classes_") and 1 in list(_model.classes_) else 0
        score = float(proba[pos_idx])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    if _iso is not None:
        try: score = float(_iso.transform([score])[0])
        except Exception: pass

    risk_class = "High" if score >= _threshold else "Low"
    priority, reasons = _priority_reasons(payload)

    logging.getLogger("uvicorn.error").info(
        f"[GH] score={score:.3f} thr={_threshold:.3f} → {risk_class}; priority={priority}"
    )

    created_iso = None
    if payload.patient_id:
        try:
            save_prediction(db, int(payload.patient_id), risk_class, round(score, 4),
                            priority, reasons, _threshold)
            row = latest_prediction(db, int(payload.patient_id))
            created_iso = row["created_at"].isoformat() if row and row.get("created_at") else None
        except Exception as e:
            logging.getLogger("uvicorn.error").warning(f"[GH] save failed: {e}")

    return PredictOut(
        risk_score=round(score, 4),
        risk_class=risk_class,
        threshold_used=_threshold,
        priority=priority,
        reasons=reasons,
        created_at=created_iso
    )

# -------------------------------------------------
#             GET LATEST PREDICTION
# -------------------------------------------------
@router.get("/gh/latest/{patient_id}", response_model=PredictOut)
def get_latest(patient_id: int, db: Session = Depends(get_db)):
    row = latest_prediction(db, patient_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not Found")

    reasons = row["reasons"]
    if isinstance(reasons, str):
        try: reasons = json.loads(reasons)
        except Exception: reasons = [reasons]

    return PredictOut(
        risk_score=float(row["risk_score"]),
        risk_class=row["risk_class"],
        threshold_used=float(row["threshold_used"]),
        priority=bool(row["priority"]),
        reasons=reasons,
        created_at=row["created_at"].isoformat() if row.get("created_at") else None
    )
