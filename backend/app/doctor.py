# backend/app/doctor.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from .db import get_db  # your existing dependency that yields a Session

router = APIRouter(prefix="/doctor", tags=["doctor"])

# ---------- Schemas ----------
class AdviceCreate(BaseModel):
    patient_id: int = Field(..., gt=0)
    doctor_id: int = Field(..., gt=0)
    text: str = Field(..., min_length=3, max_length=5000)

class AdviceOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    text: str
    created_at: datetime
    doctor_name: Optional[str] = None

# ---------- Endpoints ----------

@router.post("/advice", response_model=AdviceOut)
def create_advice(body: AdviceCreate, db: Session = Depends(get_db)):
    # Ensure patient exists
    patient = db.execute(
        text("SELECT id FROM users WHERE id = :pid AND role = 'patient'"),
        {"pid": body.patient_id}
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Ensure doctor exists
    doctor = db.execute(
        text("SELECT id, full_name FROM users WHERE id = :did AND role = 'doctor'"),
        {"did": body.doctor_id}
    ).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Insert advice
    row = db.execute(
        text("""
            INSERT INTO advice (patient_id, doctor_id, text)
            VALUES (:patient_id, :doctor_id, :text)
            RETURNING id, patient_id, doctor_id, text, created_at
        """),
        {"patient_id": body.patient_id, "doctor_id": body.doctor_id, "text": body.text}
    ).first()
    db.commit()

    return AdviceOut(
        id=row.id,
        patient_id=row.patient_id,
        doctor_id=row.doctor_id,
        text=row.text,
        created_at=row.created_at,
        doctor_name=doctor.full_name
    )

@router.get("/advice/{patient_id}", response_model=List[AdviceOut])
def list_advice_for_patient(patient_id: int, db: Session = Depends(get_db)):
    # Returns latest first
    rows = db.execute(
        text("""
            SELECT a.id, a.patient_id, a.doctor_id, a.text, a.created_at, u.full_name as doctor_name
            FROM advice a
            LEFT JOIN users u ON a.doctor_id = u.id
            WHERE a.patient_id = :pid
            ORDER BY a.created_at DESC
        """),
        {"pid": patient_id}
    ).fetchall()

    return [
        AdviceOut(
            id=r.id,
            patient_id=r.patient_id,
            doctor_id=r.doctor_id,
            text=r.text,
            created_at=r.created_at,
            doctor_name=getattr(r, "doctor_name", None),
        )
        for r in rows
    ]
