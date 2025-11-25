from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Date,
    UniqueConstraint,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import synonym

from .db import Base


# -------------------------
# Roles
# -------------------------
class UserRole(PyEnum):
    patient = "patient"
    clinician = "clinician"
    doctor = "doctor"
    admin = "admin"


# -------------------------
# Users
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Auth identifiers
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Your auth.py uses "phone", so we store it as "phone".
    # For backward compatibility with any existing code that referenced
    # "phone_number", we expose a "phone_number" synonym below.
    phone = Column(String(32), unique=True, index=True, nullable=True)
    phone_number = synonym("phone")  # <- do NOT create another column

    # Firebase linkage (used by Google sign-in / phone OTP)
    firebase_uid = Column(String(256), unique=True, index=True, nullable=True)

    # Password is optional because you’re doing email-link / Google / phone.
    password_hash = Column(String(255), nullable=True)

    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole, name="user_role_enum"), nullable=False)

    # Optional TOTP
    totp_secret = Column(String(128), nullable=True)
    totp_enabled = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Defensive uniqueness and helpful composite index for lookups
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("firebase_uid", name="uq_users_firebase_uid"),
        Index("ix_users_identity", "email", "phone", "firebase_uid"),
    )


# -------------------------
# Patients
# -------------------------
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    # one-to-one with users.id
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Optional hospital MRN
    medical_record_number = Column(String(64), unique=True, index=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_patients_user_id"),
    )


# -------------------------
# Doctor Advice (for patient dashboard)
# -------------------------
class DoctorAdvice(Base):
    __tablename__ = "doctor_advice"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# -------------------------
# Appointments / ANC Visits
# -------------------------
class AppointmentStatus(PyEnum):
    scheduled = "scheduled"
    completed = "completed"
    rescheduled = "rescheduled"
    cancelled = "cancelled"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)

    # Keep it nullable=True for safety; your logic can fill it from next_visit
    scheduled_for = Column(Date, nullable=True)

    status = Column(
        Enum(AppointmentStatus, name="appointment_status_enum"),
        default=AppointmentStatus.scheduled,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # For UI logic you mentioned
    last_visit = Column(Date, nullable=True)
    next_visit = Column(Date, nullable=True)
