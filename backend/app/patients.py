# app/patients.py
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from .db import get_db, Base, engine
from .models_risk import PatientAdvice  # ORM for advice table

# Ensure tables exist (advice table etc.)
Base.metadata.create_all(bind=engine)

router = APIRouter(tags=["patients"])

# ---------- Schemas ----------
class AdviceIn(BaseModel):
    advice: str = Field(..., min_length=1, max_length=5000)

class AdviceOut(BaseModel):
    id: int
    patient_id: int
    text: str
    created_at: str

class PatientRow(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    next_visit: Optional[str] = None
    appt_status: Optional[str] = None

class PatientDetail(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    last_visit: Optional[str] = None
    next_visit: Optional[str] = None
    appt_status: Optional[str] = None
    vitals: Optional[dict] = None
    advice: List[AdviceOut] = []

# ---------- Advice ----------
@router.post("/patients/{patient_id}/advice")
def add_advice(patient_id: int, payload: AdviceIn, db: Session = Depends(get_db)):
    # Ensure patient exists
    ok = db.execute(
        text("SELECT 1 FROM patients WHERE id = :pid LIMIT 1"),
        {"pid": patient_id}
    ).first()
    if not ok:
        raise HTTPException(status_code=404, detail="Patient not found")

    txt = payload.advice.strip()
    if not txt:
        raise HTTPException(status_code=400, detail="Advice cannot be empty")

    adv = PatientAdvice(patient_id=patient_id, text=txt)
    db.add(adv)
    db.commit()
    db.refresh(adv)
    return {"ok": True, "id": adv.id}

@router.get("/patients/{patient_id}/advice", response_model=List[AdviceOut])
def list_advice(patient_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(PatientAdvice)
          .filter(PatientAdvice.patient_id == patient_id)
          .order_by(PatientAdvice.created_at.desc(), PatientAdvice.id.desc())
          .all()
    )
    return [
        AdviceOut(
            id=r.id,
            patient_id=r.patient_id,
            text=r.text,
            created_at=r.created_at.isoformat()
        )
        for r in rows
    ]

# ---------- Resolve (email or ID) ----------
@router.get("/patients/resolve")
@router.get("/patients/resolve")
def resolve_patient(
    q: str = Query(..., min_length=1),
    create_if_missing: bool = False,
    db: Session = Depends(get_db),
):
    qs = q.strip()

    # If numeric, treat as patient_id
    if qs.isdigit():
        row = db.execute(text("""
            SELECT p.id, COALESCE(u.full_name, u.email) AS full_name, u.email
            FROM patients p
            JOIN users u ON u.id = p.user_id
            WHERE p.id = :pid
            LIMIT 1
        """), {"pid": int(qs)}).mappings().first()
        return row or {}

    # If email
    if "@" in qs:
        # 1) Return existing patient for this email if present
        row = db.execute(text("""
            SELECT p.id, COALESCE(u.full_name, u.email) AS full_name, u.email
            FROM users u
            JOIN patients p ON p.user_id = u.id
            WHERE lower(u.email) = lower(:em)
            LIMIT 1
        """), {"em": qs}).mappings().first()
        if row:
            return row

        # 2) Optionally create missing user/patient
        if create_if_missing:
            # ensure a users row exists
            urow = db.execute(text("""
                SELECT id, COALESCE(full_name, email) AS full_name, email
                FROM users
                WHERE lower(email) = lower(:em)
                LIMIT 1
            """), {"em": qs}).mappings().first()

            if not urow:
                # minimal user: email + role patient; password can be NULL
                urow = db.execute(text("""
                    INSERT INTO users (email, role)
                    VALUES (:em, 'patient')
                    RETURNING id, email
                """), {"em": qs}).mappings().first()
                db.commit()

            # ensure a patients row linked to that user
            prow = db.execute(text("""
                SELECT p.id
                FROM patients p
                WHERE p.user_id = :uid
                LIMIT 1
            """), {"uid": urow["id"]}).mappings().first()

            if not prow:
                prow = db.execute(text("""
                    INSERT INTO patients (user_id)
                    VALUES (:uid)
                    RETURNING id
                """), {"uid": urow["id"]}).mappings().first()
                db.commit()

            return {
                "id": prow["id"],
                "full_name": urow.get("full_name") if "full_name" in urow else urow["email"],
                "email": urow["email"],
            }

        # Not allowed to create → unresolved
        return {}

    # Name fallback (best match)
    row = db.execute(text("""
        SELECT p.id, COALESCE(u.full_name, u.email) AS full_name, u.email
        FROM users u
        JOIN patients p ON p.user_id = u.id
        WHERE lower(COALESCE(u.full_name,'')) LIKE lower('%' || :qq || '%')
        ORDER BY u.full_name NULLS LAST, u.email
        LIMIT 1
    """), {"qq": qs}).mappings().first()
    return row or {}


# ---------- List (search) ----------
@router.get("/patients", response_model=List[PatientRow])
def list_patients(q: Optional[str] = None, db: Session = Depends(get_db)):
    sql = text("""
        SELECT p.id,
               COALESCE(u.full_name, u.email) AS full_name,
               u.email,
               u.phone AS phone_number,
               (
                 SELECT to_char(a.next_visit, 'YYYY-MM-DD')
                 FROM appointments a
                 WHERE a.patient_id = p.id
                 ORDER BY a.next_visit DESC NULLS LAST, a.id DESC
                 LIMIT 1
               ) AS next_visit,
               (
                 SELECT a.status
                 FROM appointments a
                 WHERE a.patient_id = p.id
                 ORDER BY a.next_visit DESC NULLS LAST, a.id DESC
                 LIMIT 1
               ) AS appt_status
        FROM patients p
        JOIN users u ON u.id = p.user_id
        WHERE (:qq IS NULL)
           OR (lower(u.email) LIKE lower('%' || :qq || '%')
            OR  lower(COALESCE(u.full_name,'')) LIKE lower('%' || :qq || '%'))
        ORDER BY COALESCE(u.full_name, u.email)
        LIMIT 200
    """)
    rows = db.execute(sql, {"qq": (q or None)}).mappings().all()
    return rows

# ---------- Detail ----------
@router.get("/patients/{patient_id}", response_model=PatientDetail)
def patient_detail(patient_id: int, db: Session = Depends(get_db)):
    base = db.execute(text("""
        SELECT p.id,
               COALESCE(u.full_name, u.email) AS full_name,
               u.email,
               u.phone AS phone_number
        FROM patients p
        JOIN users u ON u.id = p.user_id
        WHERE p.id = :pid
        LIMIT 1
    """), {"pid": patient_id}).mappings().first()
    if not base:
        raise HTTPException(status_code=404, detail="Patient not found")

    appt = db.execute(text("""
        SELECT to_char(a.last_visit, 'YYYY-MM-DD') AS last_visit,
               to_char(a.next_visit, 'YYYY-MM-DD') AS next_visit,
               a.status AS appt_status
        FROM appointments a
        WHERE a.patient_id = :pid
        ORDER BY a.next_visit DESC NULLS LAST, a.id DESC
        LIMIT 1
    """), {"pid": patient_id}).mappings().first() or {}

    advice_rows = (
        db.query(PatientAdvice)
          .filter(PatientAdvice.patient_id == patient_id)
          .order_by(PatientAdvice.created_at.desc(), PatientAdvice.id.desc())
          .all()
    )
    advice = [
        AdviceOut(
            id=r.id,
            patient_id=r.patient_id,
            text=r.text,
            created_at=r.created_at.isoformat()
        )
        for r in advice_rows
    ]

    return PatientDetail(
        id=base["id"],
        full_name=base["full_name"],
        email=base["email"],
        phone_number=base["phone_number"],
        last_visit=appt.get("last_visit"),
        next_visit=appt.get("next_visit"),
        appt_status=appt.get("appt_status"),
        advice=advice
    )

# ---------- Convenience for Patient dashboard ----------
@router.get("/patients/by-email/{email}", response_model=PatientDetail)
def patient_by_email(email: str, db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT p.id
        FROM users u
        JOIN patients p ON p.user_id = u.id
        WHERE lower(u.email) = lower(:em)
        LIMIT 1
    """), {"em": email}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient_detail(row["id"], db)
