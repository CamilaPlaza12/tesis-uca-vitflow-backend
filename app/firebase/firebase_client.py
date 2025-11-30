# app/firebase/firebase_client.py
from firebase_admin import credentials, initialize_app, firestore
from app.core.config import FIREBASE_CREDENTIALS_PATH

if not FIREBASE_CREDENTIALS_PATH:
    raise RuntimeError("FIREBASE_CREDENTIALS_PATH no está configurado en .env")

cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
firebase_app = initialize_app(cred)

# Cliente de Firestore
db = firestore.client()
