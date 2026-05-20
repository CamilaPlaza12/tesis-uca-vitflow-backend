import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app.core.config import PROJECT_NAME, API_V1_PREFIX
from app.api.v1.routers import auth_router, appointment_router, availability_router, blood_bank_router, emails_router, home_router, hospital_onboarding_router, user_router, hospital_request_router, donor_router
from app.api.v1.routers import stock_router
from app.api.v1.routers import donacion_router
from app.api.v1.routers import evento_router
from app.firebase import firebase_client

app = FastAPI(title=PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:8000",
        "https://vitflow-mu.vercel.app",
        "https://vitflow-cplaza-finals-projects.vercel.app",
        "https://tesis-uca-vitflow-bot.onrender.com"
        
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
app.include_router(availability_router.router, prefix=API_V1_PREFIX)
app.include_router(donor_router.router, prefix=API_V1_PREFIX)
app.include_router(blood_bank_router.router, prefix=API_V1_PREFIX)
app.include_router(hospital_onboarding_router.router, prefix=API_V1_PREFIX)
app.include_router(home_router.router, prefix=API_V1_PREFIX)
app.include_router(stock_router.router, prefix=API_V1_PREFIX)
app.include_router(donacion_router.router, prefix=API_V1_PREFIX)
app.include_router(evento_router.router, prefix=API_V1_PREFIX)



