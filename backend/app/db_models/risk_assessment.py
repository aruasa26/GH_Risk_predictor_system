# app/db_models/risk_assessment.py
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import relationship
from app.db import Base  # your existing Base from app.db

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    model_name = Column(String, default="tabnet", nullable=False)
    model_version = Column(String, default="v1", nullable=False)

    risk_score = Column(Float, nullable=False)      # probability 0..1
    risk_class = Column(String, nullable=False)     # "Low" | "Moderate" | "High"
    threshold  = Column(Float, nullable=False)      # operating point used
    tier2_priority = Column(Integer, default=0)     # 1 if passes Tier-2 rules

    features = Column(JSON, nullable=False)         # inputs used (for audit)

    patient = relationship("Patient", backref="risk_assessments")
