# app/firebase/firebase_client.py
import os
import json
from firebase_admin import credentials, initialize_app, firestore

FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")

if not FIREBASE_CREDENTIALS_PATH:
    raise RuntimeError("FIREBASE_CREDENTIALS_PATH no está configurado en .env")

# Intentar parsear como JSON (para producción), si falla usar como ruta (para local)
try:
    cred_dict = json.loads(FIREBASE_CREDENTIALS_PATH)
    cred = credentials.Certificate(cred_dict)
except (json.JSONDecodeError, ValueError):
    # Es una ruta a archivo (uso local)
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)

firebase_app = initialize_app(cred)

# Cliente de Firestore
db = firestore.client()