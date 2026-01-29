from fastapi import HTTPException
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from google.cloud import firestore
from google.cloud.firestore import Transaction

from app.firebase.firebase_client import db

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

AVAILABLE_SLOTS_COLLECTION = "available_slots"
HOSPITAL_AVAILABILITY_COLLECTION = "hospital_availability"

MIN_TIME = time(7, 0)
END_EXCLUSIVE = time(20, 0)


def build_slot_key(hospital_id: str, date_local: date, time_local: str) -> str:
    return f"{hospital_id}_{date_local.isoformat()}_{time_local}"


def weekday_str(d: date) -> str:
    mapping = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    return mapping[d.weekday()]


def parse_hhmm(time_local: str) -> time:
    try:
        hh, mm = time_local.split(":")
        return time(int(hh), int(mm))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time_local format (expected HH:MM)")


def validate_time_rules(t: time):
    if t < MIN_TIME or t >= END_EXCLUSIVE:
        raise HTTPException(
            status_code=400,
            detail=f"time_local must be between {MIN_TIME.strftime('%H:%M')} and 19:30",
        )

def get_capacity_from_availability(hospital_id: str, date_local: date, time_local: str) -> int:
    day = weekday_str(date_local)
    if day == "Domingo":
        raise HTTPException(status_code=400, detail="No se pueden crear turnos los domingos")

    avail_ref = db.collection(HOSPITAL_AVAILABILITY_COLLECTION).document(hospital_id)
    snap = avail_ref.get()
    if not snap.exists:
        raise HTTPException(status_code=409, detail="El hospital no configuró su disponibilidad")

    data = snap.to_dict() or {}
    days = data.get("days") or []

    # buscar el día
    day_obj = next((d for d in days if d.get("day") == day), None)
    if not day_obj:
        raise HTTPException(status_code=409, detail=f"El hospital no tiene habilitado {day}")

    if not day_obj.get("enabled", False):
        raise HTTPException(status_code=409, detail=f"El hospital no tiene habilitado {day}")

    # buscar el horario
    slots = day_obj.get("timeSlots") or []
    slot = next((s for s in slots if s.get("time") == time_local), None)
    if not slot:
        raise HTTPException(
            status_code=409,
            detail=f"El hospital no tiene habilitado {day} {time_local}",
        )

    capacity = int(slot.get("capacity", 0))
    if capacity < 1:
        raise HTTPException(status_code=409, detail="Invalid capacity for selected slot")

    return capacity



def reserve_slot_service(hospital_id: str, date_local: date, time_local: str) -> str:
    t = parse_hhmm(time_local)
    validate_time_rules(t)

    capacity = get_capacity_from_availability(hospital_id, date_local, time_local)

    slot_key = build_slot_key(hospital_id, date_local, time_local)
    slot_ref = db.collection(AVAILABLE_SLOTS_COLLECTION).document(slot_key)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = slot_ref.get(transaction=tx)

        if not snap.exists:
            tx.set(slot_ref, {
                "hospital_id": hospital_id,
                "date_local": date_local.isoformat(),
                "time_local": time_local,
                "capacity": capacity,
                "used": 1,
            })
            return

        doc = snap.to_dict() or {}
        used = int(doc.get("used", 0))
        cap = int(doc.get("capacity", capacity))

        if used >= cap:
            raise HTTPException(status_code=409, detail="No hay cupos disponibles para ese horario")

        tx.update(slot_ref, {"used": used + 1})

    tx = db.transaction()
    _tx(tx)

    return slot_key


def release_slot_service(hospital_id: str, date_local: date, time_local: str):
    slot_key = build_slot_key(hospital_id, date_local, time_local)
    slot_ref = db.collection(AVAILABLE_SLOTS_COLLECTION).document(slot_key)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = slot_ref.get(transaction=tx)
        if not snap.exists:
            return

        doc = snap.to_dict() or {}
        used = int(doc.get("used", 0))

        new_used = used - 1

        # ✅ si queda 0 o menos, borramos el doc
        if new_used <= 0:
            tx.delete(slot_ref)
            return

        tx.update(slot_ref, {"used": new_used})
        
    tx = db.transaction()
    _tx(tx)


