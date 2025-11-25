# backend/app/appointments.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

from .db import get_db

router = APIRouter(prefix="/appointments", tags=["appointments"])

# ---------- Schemas ----------
class ScheduleBody(BaseModel):
    patient_id: int = Field(..., gt=0)
    last_visit_date: datetime     # ISO string from frontend
    interval_weeks: int = Field(4, ge=1, le=12)

class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    scheduled_for: datetime
    status: str

class RescheduleBody(BaseModel):
    appointment_id: int = Field(..., gt=0)
    new_date: datetime

class ConfirmBody(BaseModel):
    appointment_id: int = Field(..., gt=0)

# ---------- Helpers ----------
MAX_RESCHEDULE_DAYS = 7

def to_aware(dt: datetime) -> datetime:
    # ensure timezone-aware (UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# ---------- Endpoints ----------

@router.post("/schedule-next", response_model=AppointmentOut)
def schedule_next_anc(body: ScheduleBody, db: Session = Depends(get_db)):
    # Check patient exists
    patient = db.execute(
        text("SELECT id FROM users WHERE id = :pid AND role = 'patient'"),
        {"pid": body.patient_id}
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    last_dt = to_aware(body.last_visit_date)
    next_dt = last_dt + timedelta(weeks=body.interval_weeks)

    # Create appointment
    row = db.execute(
        text("""
            INSERT INTO appointments (patient_id, scheduled_for, status)
            VALUES (:pid, :scheduled_for, 'scheduled')
            RETURNING id, patient_id, scheduled_for, status
        """),
        {"pid": body.patient_id, "scheduled_for": next_dt}
    ).first()
    db.commit()

    return AppointmentOut(
        id=row.id, patient_id=row.patient_id,
        scheduled_for=row.scheduled_for, status=row.status
    )

@router.get("/next/{patient_id}", response_model=Optional[AppointmentOut])
def get_next_appointment(patient_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            SELECT id, patient_id, scheduled_for, status
            FROM appointments
            WHERE patient_id = :pid AND status IN ('scheduled','rescheduled','confirmed')
            ORDER BY scheduled_for ASC
            LIMIT 1
        """),
        {"pid": patient_id}
    ).first()

    if not row:
        return None

    return AppointmentOut(
        id=row.id, patient_id=row.patient_id,
        scheduled_for=row.scheduled_for, status=row.status
    )

@router.post("/confirm", response_model=AppointmentOut)
def confirm_attendance(body: ConfirmBody, db: Session = Depends(get_db)):
    # Update to confirmed
    row = db.execute(
        text("""
            UPDATE appointments
            SET status='confirmed', updated_at=NOW()
            WHERE id = :aid
            RETURNING id, patient_id, scheduled_for, status
        """),
        {"aid": body.appointment_id}
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Appointment not found")
    db.commit()
    return AppointmentOut(
        id=row.id, patient_id=row.patient_id,
        scheduled_for=row.scheduled_for, status=row.status
    )

@router.post("/reschedule", response_model=AppointmentOut)
def reschedule_appointment(body: RescheduleBody, db: Session = Depends(get_db)):
    appt = db.execute(
        text("SELECT id, scheduled_for FROM appointments WHERE id = :aid"),
        {"aid": body.appointment_id}
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    old_dt = to_aware(appt.scheduled_for)
    new_dt = to_aware(body.new_date)
    delta_days = abs((new_dt - old_dt).days)

    if delta_days > MAX_RESCHEDULE_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Reschedule limited to ±{MAX_RESCHEDULE_DAYS} days to reduce missed ANC visits"
        )

    row = db.execute(
        text("""
            UPDATE appointments
            SET scheduled_for = :new_dt, status='rescheduled', updated_at=NOW()
            WHERE id = :aid
            RETURNING id, patient_id, scheduled_for, status
        """),
        {"new_dt": new_dt, "aid": body.appointment_id}
    ).first()
    db.commit()

    return AppointmentOut(
        id=row.id, patient_id=row.patient_id,
        scheduled_for=row.scheduled_for, status=row.status
    )
