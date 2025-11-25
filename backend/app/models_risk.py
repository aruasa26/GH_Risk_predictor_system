# backend/models_risk.py
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, Text, DateTime
from .db import Base

class RiskPrediction(Base):
    __tablename__ = "risk_predictions"
    id = Column(Integer, primary_key=True, index=True)

    # Who
    patient_id = Column(Integer, index=True, nullable=True)

    # Model outputs
    risk_class = Column(String(16), nullable=False)          # "High" / "Low" (or Moderate if you add)
    risk_score = Column(Float, nullable=False)
    priority   = Column(Boolean, default=False)

    # Human-readable reasons (JSON stringified list)
    reasons_json = Column(Text, nullable=False, default="[]")

    # Snapshot of inputs used (helpful for audit / doctor view)
    age = Column(Integer, nullable=True)
    bmi = Column(Float,   nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    heart_rate   = Column(Integer, nullable=True)
    previous_complications = Column(Integer, default=0)
    preexisting_diabetes   = Column(Integer, default=0)
    gestational_diabetes   = Column(Integer, default=0)
    mental_health          = Column(Integer, default=0)

    source = Column(String(16), default="clinician")  # e.g. "clinician", "api"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PatientAdvice(Base):
    __tablename__ = "patient_advice"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, index=True, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class PatientRisk(Base):
    __tablename__ = "patient_risk"
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, index=True, nullable=False, unique=True)  # store latest per patient
    risk_class = Column(String(16), nullable=False)  # "High" / "Low"
    risk_score = Column(Float, nullable=False)
    priority = Column(Boolean, default=False)
    reasons_json = Column(Text, nullable=True)  # JSON-encoded list for portability
    screen_thr = Column(Float, nullable=True)
    priority_thr = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
