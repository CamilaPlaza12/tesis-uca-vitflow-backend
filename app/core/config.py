import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME = os.getenv("PROJECT_NAME", "VitFlow")
API_V1_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
VITO_NOTIFY_URL = os.getenv("VITO_NOTIFY_URL", "")
VITO_NOTIFY_TIMEOUT = float(os.getenv("VITO_NOTIFY_TIMEOUT", "10"))
