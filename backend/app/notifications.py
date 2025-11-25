# notifications.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from pathlib import Path
from dotenv import load_dotenv
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

from typing import List, Optional
import os, smtplib, ssl, socket
from email.message import EmailMessage
from datetime import datetime
import logging

router = APIRouter(prefix="/notifications", tags=["notifications"])
log = logging.getLogger("uvicorn.error")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
APP_NAME  = os.getenv("APP_NAME", "GH Risk Predictor")
DEV_MAIL_DIR = os.getenv("DEV_MAIL_DIR", "")      # optional local file outbox
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "12"))

def _smtp_connect_and_auth():
    """
    Connect and authenticate; returns an smtplib SMTP/SMTP_SSL instance.
    Supports STARTTLS on 587 and SMTPS on 465.
    """
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and SMTP_FROM):
        raise RuntimeError("CONFIG_MISSING: Set SMTP_HOST/PORT/USER/PASS/FROM.")

    # 465 => SMTPS; 587 => STARTTLS
    if SMTP_PORT == 465:
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT, context=context)
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        return server
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        return server

def _send_email(to_email: str, subject: str, text: str, html: Optional[str] = None):
    # Dev “file outbox” so UI keeps working even if SMTP is down
    if DEV_MAIL_DIR:
        os.makedirs(DEV_MAIL_DIR, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        fn = os.path.join(DEV_MAIL_DIR, f"{ts}-{to_email}.eml")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"From: {SMTP_FROM or '<unset>'}\nTo: {to_email}\nSubject: {subject}\n\n{text}\n\n{html or ''}")
        return

    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and SMTP_FROM):
        raise RuntimeError("CONFIG_MISSING: Set SMTP_HOST/PORT/USER/PASS/FROM.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(text or "")
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        server = _smtp_connect_and_auth()
        server.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        # Wrong password / missing Gmail App Password
        raise RuntimeError(f"AUTH_FAILED: {e}")
    except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, socket.timeout, OSError) as e:
        # Port blocked / host unreachable / TLS handshake issues
        raise RuntimeError(f"NETWORK_ERROR: {e}")
    finally:
        try:
            server.quit()
        except Exception:
            pass

# -----------------------------
# Schemas
# -----------------------------
class SendEmailIn(BaseModel):
    email: EmailStr
    subject: str
    text: Optional[str] = ""
    html: Optional[str] = None

class PredictionPayload(BaseModel):
    risk_class: str
    risk_score: float
    priority: bool = False
    reasons: Optional[List[str]] = []
    created_at: Optional[str] = None

class SendPredictionIn(BaseModel):
    email: EmailStr
    prediction: PredictionPayload

class SendVisitIn(BaseModel):
    email: EmailStr
    last_visit: str
    next_visit: Optional[str] = None

# -----------------------------
# Routes
# -----------------------------
@router.get("/diag")
def notifications_diag():
    """
    Non-destructive health check: verifies config and attempts SMTP connect+auth.
    Does NOT send an email.
    """
    status = "OK"
    detail = ""
    try:
        if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS and SMTP_FROM):
            raise RuntimeError("CONFIG_MISSING")
        srv = _smtp_connect_and_auth()
        try:
            srv.noop()
        finally:
            try: srv.quit()
            except: pass
    except Exception as e:
        status = "ERROR"
        detail = str(e)
        log.error("notifications/diag: %s", detail)

    return {
        "status": status,                 # OK or ERROR
        "detail": detail,                 # CONFIG_MISSING / AUTH_FAILED / NETWORK_ERROR / ...
        "host": SMTP_HOST, "port": SMTP_PORT,
        "user_set": bool(SMTP_USER),
        "pass_set": bool(SMTP_PASS),
        "from_set": bool(SMTP_FROM),
        "dev_outbox": bool(DEV_MAIL_DIR),
        "app_name": APP_NAME,
    }

@router.post("/send-email")
def send_email_generic(body: SendEmailIn):
    try:
        _send_email(body.email, body.subject, body.text or "", body.html)
        return {"ok": True}
    except Exception as e:
        log.exception("send-email failed")
        raise HTTPException(status_code=502, detail=f"{e}")

@router.post("/send-prediction")
def send_prediction(body: SendPredictionIn):
    p = body.prediction
    when = p.created_at
    try:
        dt = datetime.fromisoformat(when.replace("Z","")) if when else datetime.utcnow()
    except Exception:
        dt = datetime.utcnow()

    reasons_text = ""
    if p.reasons:
        reasons_text = "\nReasons: " + ", ".join([str(r) for r in p.reasons])

    subject = f"{APP_NAME}: Your Latest GH Risk Prediction"
    text = (
        f"Hello,\n\n"
        f"Here is your latest GH screening result:\n"
        f"• Risk: {p.risk_class}\n"
        f"• Score: {p.risk_score}\n"
        f"• Priority band: {'Yes' if p.priority else 'No'}"
        f"{reasons_text}\n\n"
        f"Assessed on: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"This screening supports — not replaces — clinical judgment.\n"
        f"- {APP_NAME}\n"
    )
    try:
        _send_email(body.email, subject, text)
        return {"ok": True}
    except Exception as e:
        log.exception("send-prediction failed")
        raise HTTPException(status_code=502, detail=f"{e}")

@router.post("/send-visit")
def send_visit(body: SendVisitIn):
    subject = f"{APP_NAME}: ANC Visit Details"
    nxt = body.next_visit or "(to be confirmed)"
    text = (
        "Hello,\n\n"
        "Your ANC visit details are below:\n"
        f"• Last visit: {body.last_visit}\n"
        f"• Next visit: {nxt}\n\n"
        "Please attend your appointment for a comprehensive check-up.\n"
        f"- {APP_NAME}\n"
    )
    try:
        _send_email(body.email, subject, text)
        return {"ok": True}
    except Exception as e:
        log.exception("send-visit failed")
        raise HTTPException(status_code=502, detail=f"{e}")
