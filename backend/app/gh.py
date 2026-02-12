# backend/app/gh.py
from __future__ import annotations
import os, json
from typing import List, Dict, Optional
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .db import get_db
from .models_risk import PatientRisk

ROOT_ML   = "/Users/caesararuasa/GH_Risk_predictor_system/ml_model"
ROOT_OUT  = "/Users/caesararuasa/GH_Risk_predictor_system/backend/ml_model"

MODEL_PATH   = os.path.join(ROOT_OUT, "tabnet_model.pkl")
CALIBRATOR   = os.path.join(ROOT_OUT, "isotonic_calibrator.pkl")
FEAT_JSON    = os.path.join(ROOT_OUT, "feature_order.json")
THRESHOLDS   = os.path.join(ROOT_OUT, "threshold.json")
XTRAIN_PATH  = os.path.join(ROOT_ML,  "X_train.csv")

if not os.path.isfile(MODEL_PATH):
    raise RuntimeError(f"Model not found: {MODEL_PATH}")
if not os.path.isfile(FEAT_JSON):
    raise RuntimeError(f"feature_order.json not found: {FEAT_JSON}")

clf = joblib.load(MODEL_PATH)
try:
    calibrator = joblib.load(CALIBRATOR) if os.path.isfile(CALIBRATOR) else None
except Exception:
    calibrator = None

with open(FEAT_JSON) as f:
    FEATURE_ORDER: List[str] = json.load(f)

if os.path.isfile(XTRAIN_PATH):
    _Xtrain = pd.read_csv(XTRAIN_PATH)
    TRAIN_MEDIANS: Dict[str, float] = {c: float(pd.to_numeric(_Xtrain[c], errors="coerce").median()) for c in _Xtrain.columns}
else:
    TRAIN_MEDIANS = {c: 0.0 for c in FEATURE_ORDER}

DEFAULT_SCREEN_T = 0.03
DEFAULT_PRIOR_T  = 0.26

screen_thr = DEFAULT_SCREEN_T
prior_thr  = DEFAULT_PRIOR_T
if os.path.isfile(THRESHOLDS):
    try:
        t = json.load(open(THRESHOLDS))
        if "screen_threshold" in t: screen_thr = float(t["screen_threshold"])
        if "priority_threshold" in t: prior_thr  = float(t["priority_threshold"])
        if "threshold" in t:
            prior_thr = float(t["threshold"])
    except Exception:
        pass

screen_thr = float(os.environ.get("GH_SCREEN_T", screen_thr))
prior_thr  = float(os.environ.get("GH_PRIORITY_T", prior_thr))

class PredictPayload(BaseModel):
  # patient_id is optional; when present we’ll persist the result for that patient
  patient_id: Optional[int] = None
  age: int = Field(..., ge=10, le=60)
  bmi: float = Field(..., ge=10, le=60)
  systolic_bp: int = Field(..., ge=60, le=250)
  diastolic_bp: int = Field(..., ge=40, le=150)
  previous_complications: int = Field(..., ge=0, le=1)
  preexisting_diabetes: int = Field(..., ge=0, le=1)
  gestational_diabetes: int = Field(..., ge=0, le=1)
  mental_health: int = Field(..., ge=0, le=1)
  heart_rate: int = Field(..., ge=40, le=220)

class PredictResponse(BaseModel):
  risk_class: str
  risk_score: float
  priority: bool
  reasons: List[str]
  thresholds: Dict[str, float]
  created_at: Optional[str] = None

router = APIRouter(prefix="/gh", tags=["gestational-hypertension"])

def rule_reasons(p: PredictPayload) -> List[str]:
    reasons = []
    if p.systolic_bp >= 140: reasons.append(f"SBP ≥ 140 ({p.systolic_bp})")
    if p.diastolic_bp >= 90: reasons.append(f"DBP ≥ 90 ({p.diastolic_bp})")
    if p.systolic_bp >= 130 and p.diastolic_bp >= 85:
        reasons.append(f"SBP ≥ 130 & DBP ≥ 85 ({p.systolic_bp}/{p.diastolic_bp})")
    if p.bmi >= 35: reasons.append(f"BMI ≥ 35 ({p.bmi})")
    if p.age < 18 or p.age > 40: reasons.append(f"Age high-risk ({p.age})")
    if p.previous_complications == 1: reasons.append("Previous complications")
    if p.preexisting_diabetes == 1: reasons.append("Pre-existing diabetes")
    if p.gestational_diabetes == 1: reasons.append("Gestational diabetes")
    if p.mental_health == 1: reasons.append("Mental health comorbidity")
    return reasons

def make_vector(p: PredictPayload) -> np.ndarray:
    row = {c: np.nan for c in FEATURE_ORDER}
    row["Age"]                    = float(p.age)
    row["BMI"]                    = float(p.bmi)
    row["Systolic BP"]            = float(p.systolic_bp)
    row["Diastolic BP"]           = float(p.diastolic_bp)
    row["Heart Rate"]             = float(p.heart_rate)
    row["Previous Complications"] = int(p.previous_complications)
    row["Preexisting Diabetes"]   = int(p.preexisting_diabetes)
    row["Gestational Diabetes"]   = int(p.gestational_diabetes)
    row["Mental Health"]          = int(p.mental_health)

    for c in ["Gravida","Parity","Prev Preeclampsia","Chronic HTN","GDM","Anemia","Preterm Birth"]:
        if c in row: row[c] = TRAIN_MEDIANS.get(c, 0.0)
    if "source_s1" in row: row["source_s1"] = 0.0

    for c in row:
        if pd.isna(row[c]):
            row[c] = TRAIN_MEDIANS.get(c, 0.0)
    return np.array([row[c] for c in FEATURE_ORDER], dtype=np.float32).reshape(1, -1)

@router.post("/predict-gh", response_model=PredictResponse)
def predict_gh(payload: PredictPayload, db: Session = Depends(get_db)) -> PredictResponse:
    try:
        x = make_vector(payload)
        proba = float(clf.predict_proba(x)[:, 1][0])
        if calibrator is not None:
            proba = float(np.clip(calibrator.predict([proba])[0], 0.0, 1.0))

        risk_class = "High" if proba >= screen_thr else "Low"
        priority   = bool(proba >= prior_thr)
        reasons    = rule_reasons(payload)
        now_iso    = datetime.utcnow().isoformat()

        # persist (upsert) if we know the patient
        if payload.patient_id is not None:
            existing = db.query(PatientRisk).filter(PatientRisk.patient_id == payload.patient_id).one_or_none()
            if existing:
                existing.risk_class = risk_class
                existing.risk_score = proba
                existing.priority   = priority
                existing.reasons_json = json.dumps(reasons)
                existing.screen_thr = screen_thr
                existing.priority_thr = prior_thr
                existing.created_at = datetime.utcnow()
            else:
                db.add(PatientRisk(
                    patient_id   = payload.patient_id,
                    risk_class   = risk_class,
                    risk_score   = proba,
                    priority     = priority,
                    reasons_json = json.dumps(reasons),
                    screen_thr   = screen_thr,
                    priority_thr = prior_thr,
                    created_at   = datetime.utcnow()
                ))
            db.commit()

        return PredictResponse(
            risk_class=risk_class,
            risk_score=round(proba, 3),
            priority=priority,
            reasons=reasons,
            thresholds={"screen": screen_thr, "priority": prior_thr},
            created_at=now_iso
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prediction failed: {e}")

@router.get("/latest/{patient_id}", response_model=PredictResponse)
def latest_for_patient(patient_id: int, db: Session = Depends(get_db)) -> PredictResponse:
    row = db.query(PatientRisk).filter(PatientRisk.patient_id == patient_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No saved prediction for this patient.")
    # shape to match PredictResponse
    reasons = []
    try:
        if row.reasons_json:
            parsed = json.loads(row.reasons_json)
            if isinstance(parsed, list): reasons = parsed
    except Exception:
        reasons = []
    return PredictResponse(
        risk_class = row.risk_class,
        risk_score = round(float(row.risk_score), 3),
        priority   = bool(row.priority),
        reasons    = reasons,
        thresholds = {"screen": row.screen_thr or screen_thr, "priority": row.priority_thr or prior_thr},
        created_at = row.created_at.isoformat() if row.created_at else None
    )
