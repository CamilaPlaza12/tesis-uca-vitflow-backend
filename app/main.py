from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import PROJECT_NAME, API_V1_PREFIX
from app.api.v1.routers import auth_router, appointment_router, user_router, hospital_request_router
from app.firebase import firebase_client

app = FastAPI(title=PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_router.router, prefix=API_V1_PREFIX)
app.include_router(appointment_router.router, prefix=API_V1_PREFIX)
app.include_router(user_router.router, prefix=API_V1_PREFIX)
app.include_router(hospital_request_router.router, prefix=API_V1_PREFIX)

