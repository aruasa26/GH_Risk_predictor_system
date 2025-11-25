# backend/firebase_admin_init.py
import os
import firebase_admin
from firebase_admin import credentials

def _init_admin():
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # >>> YOUR ABSOLUTE PATH TO THE NEWLY REGENERATED KEY <<< 
    key_path = "/Users/caesararuasa/GH_Risk_predictor_system/backend/secrets/firebase_admin_key.json"
    if not os.path.exists(key_path):
        raise RuntimeError(f"Firebase admin key not found at {key_path}")

    cred = credentials.Certificate(key_path)
    return firebase_admin.initialize_app(cred)

app = _init_admin()
