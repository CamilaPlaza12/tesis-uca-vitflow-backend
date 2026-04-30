"""
Stub Firebase antes de que cualquier módulo de la app lo importe.
Evita que firebase_client.py falle por falta de FIREBASE_CREDENTIALS_PATH.
"""
import sys
from unittest.mock import MagicMock

# Reemplazamos el módulo firebase antes de que se importe
_firebase_mock = MagicMock()
sys.modules.setdefault("firebase_admin", _firebase_mock)
sys.modules.setdefault("firebase_admin.credentials", _firebase_mock)
sys.modules.setdefault("firebase_admin.firestore", _firebase_mock)

# Stub del cliente de Firestore usado por la app
_db_mock = MagicMock()
firebase_client_stub = MagicMock()
firebase_client_stub.db = _db_mock
sys.modules["app.firebase.firebase_client"] = firebase_client_stub
