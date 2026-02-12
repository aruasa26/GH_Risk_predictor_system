# app/ml_model.py
import os, json, joblib

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "ml_model_artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "tabnet_model.pkl")
META_PATH  = os.path.join(ARTIFACT_DIR, "model_meta.json")

_model = joblib.load(MODEL_PATH)
_meta  = json.load(open(META_PATH))
FEATURES = _meta["feature_order"]
THRESH   = float(_meta.get("threshold_test", _meta.get("threshold_oof", 0.5)))

def predict_proba_row(payload: dict):
    import numpy as np
    def cast_bool(v): return 1 if str(v).strip().lower() in ("1","true","t","yes","y") else 0
    row = []
    for f in FEATURES:
        v = payload.get(f)
        if f in ("Previous Complications","Preexisting Diabetes","Gestational Diabetes","Mental Health"):
            v = cast_bool(v)
        try: v = float(v)
        except: v = 0.0
        row.append(v)
    X = np.array(row, dtype=np.float32).reshape(1, -1)
    p = float(_model.predict_proba(X)[:,1][0])
    y = 1 if p >= THRESH else 0
    return p, y
