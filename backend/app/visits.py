from datetime import datetime, date, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import get_db
from .models import Appointment, Patient, User

router = APIRouter(prefix="/visits", tags=["visits"])

# ----------------- Helpers -----------------

def get_patient_by_email(db: Session, email: str) -> Optional[Patient]:
    """Resolve a Patient row from a user email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    return db.query(Patient).filter(Patient.user_id == user.id).first()

# ----------------- Schemas -----------------

class ScheduleVisitIn(BaseModel):
    patient_id: int
    last_visit: date
    requested_next: Optional[date] = None

class RescheduleIn(BaseModel):
    patient_id: int
    new_date: date

# ----------------- Endpoints -----------------

@router.post("/schedule")
def schedule_visit(payload: ScheduleVisitIn, db: Session = Depends(get_db)):
    """
    Creates/records the next ANC visit for a patient.
    - Next visit must be in the 3–5 week window after last_visit.
    """
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    min_date = payload.last_visit + timedelta(days=21)
    max_date = payload.last_visit + timedelta(days=35)

    # If clinician suggests a date, enforce 3–5 week window; else default to 3 weeks.
    if payload.requested_next:
        if not (min_date <= payload.requested_next <= max_date):
            raise HTTPException(status_code=400, detail="Requested next visit outside 3–5 week window")
        next_visit = payload.requested_next
    else:
        next_visit = min_date

    # Pick a default clinic time for calendar convenience (09:00)
    scheduled_dt = datetime.combine(next_visit, time(9, 0))

    appt = Appointment(
        patient_id=patient.id,
        last_visit=payload.last_visit,
        next_visit=next_visit,
        scheduled_for=scheduled_dt,
        status="scheduled",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    return {
        "ok": True,
        "appointment_id": appt.id,
        "next_visit": appt.next_visit.isoformat(),
        "status": appt.status,
        "scheduled_for": appt.scheduled_for.isoformat(),
    }

@router.get("/gh/me/next-visit")
def me_next_visit(email: str = Query(...), db: Session = Depends(get_db)):
    """
    Patient-side: get the most recent (latest) next visit by patient email.
    Returns None if patient or appointment not found.
    """
    patient = get_patient_by_email(db, email)
    if not patient:
        return {"next_visit": None}

    appt = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient.id)
        .order_by(Appointment.next_visit.desc())
        .first()
    )
    if not appt:
        return {"next_visit": None}

    return {
        "next_visit": appt.next_visit.isoformat(),
        "status": appt.status,
        "scheduled_for": appt.scheduled_for.isoformat(),
    }

@router.post("/reschedule")
def reschedule(payload: RescheduleIn, db: Session = Depends(get_db)):
    """
    Patient-initiated reschedule within ±7 days of current next_visit.
    (Your UI keeps a simple alert; clinician confirms attendance separately.)
    """
    appt = (
        db.query(Appointment)
        .filter(Appointment.patient_id == payload.patient_id)
        .order_by(Appointment.next_visit.desc())
        .first()
    )
    if not appt:
        raise HTTPException(status_code=404, detail="No appointment found")

    current = appt.next_visit
    min_allowed = current - timedelta(days=7)
    max_allowed = current + timedelta(days=7)

    if not (min_allowed <= payload.new_date <= max_allowed):
        raise HTTPException(status_code=400, detail="Reschedule must be within ±7 days")

    appt.next_visit = payload.new_date
    appt.scheduled_for = datetime.combine(payload.new_date, time(9, 0))
    appt.status = "rescheduled"
    db.commit()
    db.refresh(appt)

    return {"ok": True, "next_visit": appt.next_visit.isoformat(), "status": appt.status}
