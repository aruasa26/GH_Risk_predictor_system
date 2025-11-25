# backend/risk.py
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db, Base, engine
from .models_risk import RiskPrediction

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/risk", tags=["risk"])

class RiskOut(BaseModel):
    has_assessment: bool
    risk_class: Optional[str] = None
    risk_score: Optional[float] = None
    priority: Optional[bool] = None
    reasons: List[str] = []

@router.get("/patient/{patient_id}/latest", response_model=RiskOut)
def latest_patient_risk(patient_id: int, db: Session = Depends(get_db)) -> RiskOut:
    rec = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.patient_id == patient_id)
        .order_by(RiskPrediction.created_at.desc(), RiskPrediction.id.desc())
        .first()
    )
    if not rec:
        return RiskOut(has_assessment=False, reasons=[])

    try:
        reasons = json.loads(rec.reasons_json or "[]")
        if not isinstance(reasons, list):
            reasons = []
    except Exception:
        reasons = []

    return RiskOut(
        has_assessment=True,
        risk_class=rec.risk_class,
        risk_score=round(float(rec.risk_score), 3),
        priority=bool(rec.priority),
        reasons=reasons
    )
