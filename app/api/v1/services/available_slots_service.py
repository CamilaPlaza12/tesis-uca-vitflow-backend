from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from google.cloud import firestore
from google.cloud.firestore import Transaction

from app.firebase.firebase_client import db
from app.api.v1.services.hospital_request_service import get_hospital_request_any_service

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

    day_obj = next((d for d in days if d.get("day") == day), None)
    if not day_obj:
        raise HTTPException(status_code=409, detail=f"El hospital no tiene habilitado {day}")

    if not day_obj.get("enabled", False):
        raise HTTPException(status_code=409, detail=f"El hospital no tiene habilitado {day}")

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
            tx.set(
                slot_ref,
                {
                    "hospital_id": hospital_id,
                    "date_local": date_local.isoformat(),
                    "time_local": time_local,
                    "capacity": capacity,
                    "used": 1,
                },
            )
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

        if new_used <= 0:
            tx.delete(slot_ref)
            return

        tx.update(slot_ref, {"used": new_used})

    tx = db.transaction()
    _tx(tx)


def _time_bucket(time_local: str) -> str | None:
    try:
        hh = int(time_local[:2])
    except Exception:
        return None

    if 8 <= hh <= 11:
        return "MORNING"
    if 12 <= hh <= 14:
        return "MIDDAY"
    if 15 <= hh <= 18:
        return "AFTERNOON"

    return None


def _time_range_label(code: str) -> str:
    mapping = {
        "MORNING": "Por la mañana",
        "MIDDAY": "Mediodía",
        "AFTERNOON": "Por la tarde",
    }
    return mapping.get(code, code)


def _day_label(slot_date: date, today_ba: date) -> str:
    if slot_date == today_ba:
        return "Hoy"

    if slot_date == today_ba + timedelta(days=1):
        return "Mañana"

    weekday_map = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }

    weekday_en = slot_date.strftime("%A")
    weekday_es = weekday_map.get(weekday_en, weekday_en)
    return f"{weekday_es} {slot_date.strftime('%d/%m')}"


def _collect_all_available_slots_for_request(request_id: str, days_ahead: int = 14):
    req = get_hospital_request_any_service(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    if req.get("status") != "ACTIVO":
        raise HTTPException(status_code=409, detail="HospitalRequest is not ACTIVO")

    end_raw = req.get("end_date")
    try:
        end_dt = datetime.fromisoformat(end_raw)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=BA_TZ)
    except Exception:
        raise HTTPException(status_code=409, detail="HospitalRequest has invalid end_date")

    hospital_id = req.get("hospital_id")

    avail_ref = db.collection(HOSPITAL_AVAILABILITY_COLLECTION).document(hospital_id)
    avail_snap = avail_ref.get()
    if not avail_snap.exists:
        raise HTTPException(status_code=409, detail="El hospital no configuró su disponibilidad")

    availability = avail_snap.to_dict() or {}
    availability_days = availability.get("days") or []

    now_ba = datetime.now(BA_TZ)
    start_date = now_ba.date()
    max_date = min(
        end_dt.date(),
        start_date + timedelta(days=max(1, min(days_ahead, 60)) - 1),
    )

    results = []
    current_date = start_date

    while current_date <= max_date:
        day_name = weekday_str(current_date)
        day_cfg = next((d for d in availability_days if d.get("day") == day_name), None)

        if day_cfg and day_cfg.get("enabled", False):
            for slot in day_cfg.get("timeSlots") or []:
                time_local = slot.get("time")
                capacity = int(slot.get("capacity", 0) or 0)

                if not time_local or capacity <= 0:
                    continue

                slot_dt = datetime.combine(current_date, parse_hhmm(time_local)).replace(tzinfo=BA_TZ)
                if slot_dt < now_ba:
                    continue

                slot_key = build_slot_key(hospital_id, current_date, time_local)
                slot_snap = db.collection(AVAILABLE_SLOTS_COLLECTION).document(slot_key).get()

                used = 0
                stored_capacity = capacity

                if slot_snap.exists:
                    slot_doc = slot_snap.to_dict() or {}
                    used = int(slot_doc.get("used", 0) or 0)
                    stored_capacity = int(slot_doc.get("capacity", capacity) or capacity)

                remaining = stored_capacity - used
                if remaining <= 0:
                    continue

                results.append(
                    {
                        "date_local": current_date.isoformat(),
                        "weekday": day_name,
                        "time_local": time_local,
                        "capacity": stored_capacity,
                        "used": used,
                        "remaining": remaining,
                    }
                )

        current_date += timedelta(days=1)

    results.sort(key=lambda x: (x["date_local"], x["time_local"]))

    return {
        "hospital_request_id": request_id,
        "hospital_id": hospital_id,
        "end_date": end_dt.isoformat(),
        "slots": results,
    }


def list_available_days_for_request_service(request_id: str, days_ahead: int = 14):
    base = _collect_all_available_slots_for_request(request_id=request_id, days_ahead=days_ahead)
    all_slots = base["slots"]
    today_ba = datetime.now(BA_TZ).date()

    unique_days = []
    seen = set()

    for slot in all_slots:
        slot_date = datetime.fromisoformat(slot["date_local"]).date()
        if slot_date.isoformat() in seen:
            continue

        seen.add(slot_date.isoformat())
        unique_days.append(
            {
                "date_local": slot_date.isoformat(),
                "label": _day_label(slot_date, today_ba),
            }
        )

    return {
        "hospital_request_id": request_id,
        "hospital_id": base["hospital_id"],
        "total": len(unique_days),
        "days": unique_days,
    }


def list_available_time_ranges_for_request_service(request_id: str, date_local: date):
    base = _collect_all_available_slots_for_request(request_id=request_id, days_ahead=60)
    all_slots = base["slots"]

    same_day_slots = [
        slot for slot in all_slots
        if slot["date_local"] == date_local.isoformat()
    ]

    buckets = []
    present = set()

    for slot in same_day_slots:
        bucket = _time_bucket(slot["time_local"])
        if not bucket or bucket in present:
            continue

        present.add(bucket)
        buckets.append(
            {
                "code": bucket,
                "label": _time_range_label(bucket),
            }
        )

    ordered_codes = ["MORNING", "MIDDAY", "AFTERNOON"]
    buckets.sort(key=lambda x: ordered_codes.index(x["code"]))

    return {
        "hospital_request_id": request_id,
        "hospital_id": base["hospital_id"],
        "date_local": date_local.isoformat(),
        "total": len(buckets),
        "time_ranges": buckets,
    }


def list_available_slots_for_request_service(
    request_id: str,
    date_local: date,
    time_range: str | None = None,
    limit: int = 8,
    offset: int = 0,
):
    base = _collect_all_available_slots_for_request(request_id=request_id, days_ahead=60)
    all_slots = base["slots"]

    filtered = [
        slot for slot in all_slots
        if slot["date_local"] == date_local.isoformat()
    ]

    if time_range:
        filtered = [
            slot for slot in filtered
            if _time_bucket(slot["time_local"]) == time_range
        ]

    total = len(filtered)
    sliced = filtered[offset: offset + limit]
    has_more = offset + limit < total

    return {
        "hospital_request_id": request_id,
        "hospital_id": base["hospital_id"],
        "date_local": date_local.isoformat(),
        "time_range": time_range,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "slots": sliced,
    }