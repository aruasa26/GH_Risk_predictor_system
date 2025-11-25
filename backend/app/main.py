# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .db import Base, engine
from .auth import router as auth_router
from .patients import router as patients_router
from .visits import router as visits_router
from .gh_predict import router as gh_router 
from .risk import router as risk_router  
from .notifications import router as notifications_router
from dotenv import load_dotenv
load_dotenv()
from .models_risk import RiskPrediction, PatientAdvice  #

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables (include our new models)
Base.metadata.create_all(bind=engine)

@app.get("/status")
def status():
    return {"ok": True}


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

# Routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(visits_router)
app.include_router(gh_router)    
app.include_router(risk_router) 
app.include_router(notifications_router)