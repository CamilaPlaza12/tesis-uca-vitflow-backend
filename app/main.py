import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from contextlib import asynccontextmanager
from datetime import date, timedelta
from zoneinfo import ZoneInfo
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import PROJECT_NAME, API_V1_PREFIX, VITO_BOT_BASE_URL, INTERNAL_TOKEN
from app.api.v1.routers import auth_router, appointment_router, availability_router, blood_bank_router, emails_router, home_router, hospital_onboarding_router, user_router, hospital_request_router, donor_router
from app.api.v1.routers import stock_router
from app.api.v1.routers import donacion_router
from app.api.v1.routers import evento_router
from app.firebase import firebase_client

from app.api.v1.services.appointment_service import (
    mark_past_appointments_no_presentado_service,
    get_appointments_for_reminder_service,
)

TZ_BA = ZoneInfo("America/Argentina/Buenos_Aires")


async def _job_mark_no_presentado():
    print("[SCHEDULER] Ejecutando job: marcar turnos pasados como NO_PRESENTADO")
    try:
        count = mark_past_appointments_no_presentado_service()
        print(f"[SCHEDULER] Turnos marcados NO_PRESENTADO: {count}")
    except Exception as e:
        print(f"[SCHEDULER] Error en mark_no_presentado: {e}")


async def _job_send_reminders():
    print("[SCHEDULER] Ejecutando job: enviar recordatorios 24hs")
    try:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        appointments = get_appointments_for_reminder_service(tomorrow)
        print(f"[SCHEDULER] Recordatorios a enviar: {len(appointments)}")

        base_url = (VITO_BOT_BASE_URL or "").rstrip("/")
        if not base_url:
            print("[SCHEDULER] VITO_BOT_BASE_URL no configurado, se omiten recordatorios")
            return

        async with httpx.AsyncClient(timeout=15) as client:
            for appt in appointments:
                try:
                    resp = await client.post(
                        f"{base_url}/notify/appointment-reminder",
                        json={
                            "phone_number": appt["phone_number"],
                            "donor_name": appt["donor_name"],
                            "date_local": appt["date_local"],
                            "time_local": appt["time_local"],
                            "hospital_name": appt["hospital_name"],
                        },
                        headers={"x-internal-token": INTERNAL_TOKEN or ""},
                    )
                    if resp.status_code == 200:
                        print(f"[SCHEDULER] Recordatorio enviado a {appt['phone_number']}")
                    else:
                        print(f"[SCHEDULER] Error enviando a {appt['phone_number']}: {resp.status_code}")
                except Exception as exc:
                    print(f"[SCHEDULER] Excepcion enviando a {appt.get('phone_number')}: {exc}")
    except Exception as e:
        print(f"[SCHEDULER] Error en send_reminders: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler(timezone=TZ_BA)
    scheduler.add_job(_job_mark_no_presentado, CronTrigger(hour=3, minute=0, timezone=TZ_BA))
    scheduler.add_job(_job_send_reminders, CronTrigger(hour=8, minute=0, timezone=TZ_BA))
    scheduler.start()
    print("[SCHEDULER] APScheduler iniciado")
    yield
    scheduler.shutdown(wait=False)
    print("[SCHEDULER] APScheduler detenido")


app = FastAPI(title=PROJECT_NAME, lifespan=lifespan)

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



