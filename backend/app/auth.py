from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from firebase_admin import auth as fb_auth

from .firebase_admin_init import *  # ensures firebase_admin.initialize_app(...)
from .db import SessionLocal
from .models import User, Patient, UserRole  # role is Enum(UserRole)

router = APIRouter()


class FirebaseLoginIn(BaseModel):
    id_token: str
    chosen_role: str | None = None
    ensure_patient: bool = False


def parse_role(role_str: str | None) -> UserRole | None:
    if not role_str:
        return None
    try:
        return UserRole(role_str)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid role. Use one of: patient, clinician, doctor, admin.",
        )


def upsert_user(db, *, uid, email, phone, name, role_hint: UserRole | None) -> User:
    """
    Resolve in this order: firebase_uid -> email -> phone.
    Create/update as needed. Enforce role mismatch.
    """
    user = None

    if uid:
        user = db.query(User).filter(User.firebase_uid == uid).one_or_none()
    if not user and email:
        user = db.query(User).filter(User.email == email).one_or_none()
    if not user and phone:
        user = db.query(User).filter(User.phone == phone).one_or_none()

    if not user:
        user = User(
            email=email,
            phone=phone,
            full_name=name,
            firebase_uid=uid,
            role=role_hint if role_hint else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # existing user: update identifiers
    changed = False
    if uid and user.firebase_uid != uid:
        user.firebase_uid = uid
        changed = True
    if email and user.email != email:
        user.email = email
        changed = True
    if phone and user.phone != phone:
        user.phone = phone
        changed = True

    # role enforcement
    if role_hint:
        if user.role and user.role != role_hint:
            raise HTTPException(
                status_code=409,
                detail=f"Role mismatch: your account is '{user.role.value}', not '{role_hint.value}'.",
            )
        if not user.role:
            user.role = role_hint
            changed = True

    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def ensure_patient(db, user: User) -> int | None:
    if user.role != UserRole.patient:
        return None
    pat = db.query(Patient).filter(Patient.user_id == user.id).one_or_none()
    if not pat:
        pat = Patient(user_id=user.id)
        db.add(pat)
        db.commit()
        db.refresh(pat)
    return pat.id


def handle_login(payload: FirebaseLoginIn):
    # Verify Firebase ID token
    try:
        decoded = fb_auth.verify_id_token(payload.id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    uid = decoded.get("uid")
    email = decoded.get("email")
    phone = decoded.get("phone_number")
    name = decoded.get("name")

    if not (email or phone):
        raise HTTPException(
            status_code=400,
            detail="Token missing email/phone. Enable the provider in Firebase.",
        )

    role_hint = parse_role(payload.chosen_role)

    db = SessionLocal()
    try:
        user = upsert_user(
            db, uid=uid, email=email, phone=phone, name=name, role_hint=role_hint
        )

        patient_id = None
        if payload.ensure_patient and user.role == UserRole.patient:
            patient_id = ensure_patient(db, user)

        # Return values the frontend already expects
        return {
            "token": payload.id_token,  # reuse Firebase token; swap to your own JWT later if you want
            "role": (user.role.value if user.role else None),
            "user_id": user.id,
            "patient_id": patient_id,
        }
    finally:
        db.close()


@router.post("/auth/firebase/login")
def firebase_login(payload: FirebaseLoginIn):
    return handle_login(payload)


@router.post("/auth/firebase-login")
def firebase_login_alias(payload: FirebaseLoginIn):
    return handle_login(payload)
