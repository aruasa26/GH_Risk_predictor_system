# backend/app/ml_runtime.py
import os
import json
import joblib
import numpy as np

# Artifacts produced by your training scripts
ARTIFACT_DIR = "/Users/caesararuasa/GH_Risk_predictor_system/ml_model/artifacts"
MODEL_PATH   = os.path.join(ARTIFACT_DIR, "tabnet_model.pkl")
META_PATH    = os.path.join(ARTIFACT_DIR, "model_meta.json")

_model = None
_meta  = None

def _load():
    global _model, _meta
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    if _meta is None:
        with open(META_PATH, "r") as f:
            _meta = json.load(f)
    return _model, _meta

BOOL_POS = {"1","true","t","yes","y",1,True}

def _cast_bool(v: object) -> float:
    return 1.0 if str(v).strip().lower() in BOOL_POS else 0.0

# Map React form keys -> training feature names (exact)
FEATURE_MAP = {
    "age": "Age",
    "bmi": "BMI",
    "systolic_bp": "Systolic BP",
    "diastolic_bp": "Diastolic BP",
    "heart_rate": "Heart Rate",
    "previous_complications": "Previous Complications",
    "preexisting_diabetes": "Preexisting Diabetes",
    "gestational_diabetes": "Gestational Diabetes",
    "mental_health": "Mental Health",
}

def predict_from_form(form_payload: dict):
    """
    form_payload is exactly what your ClinicianDashboard sends.
    Returns dict with probability, class (0/1), risk_class string, risk_score 0-100.
    """
    model, meta = _load()
    feature_order = meta["feature_order"]
    thr = float(meta.get("threshold_test", meta.get("threshold_oof", 0.5)))

    row = []
    for feat in feature_order:
        # find the form key for this model feature
        form_key = None
        for k, v in FEATURE_MAP.items():
            if v == feat:
                form_key = k
                break

        val = form_payload.get(form_key, None)
        # booleans
        if feat in ("Previous Complications","Preexisting Diabetes","Gestational Diabetes","Mental Health"):
            row.append(_cast_bool(val))
        else:
            try:
                row.append(float(val))
            except Exception:
                # conservative defaults if missing (prevents 500s)
                defaults = {
                    "Age": 28, "BMI": 26, "Systolic BP": 120, "Diastolic BP": 80, "Heart Rate": 80
                }
                row.append(float(defaults.get(feat, 0.0)))

    X = np.array(row, dtype=np.float32).reshape(1, -1)
    proba = float(model.predict_proba(X)[:, 1][0])
    label = int(proba >= thr)

    # Match your UI’s three badges
    margin = 0.10
    if proba >= thr + margin:
        risk_class = "High"
    elif proba <= thr - margin:
        risk_class = "Low"
    else:
        risk_class = "Moderate"

    return {
        "probability": proba,
        "class": label,
        "threshold": thr,
        "risk_score": round(proba * 100, 1),  # for your “score …” display
        "risk_class": risk_class
    }
