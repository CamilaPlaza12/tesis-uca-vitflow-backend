from app.schemas.availability_schema import HospitalAvailabilityIn, HospitalAvailabilityOut
from app.firebase.firebase_client import db

AVAILABILITY_COLL = "hospital_availability"

WEEK_DAYS = [
    "Lunes",
    "Martes",
    "Miercoles",
    "Jueves",
    "Viernes",
    "Sabado",
    "Domingo",
]


def _default_availability(hospital_id: str) -> HospitalAvailabilityOut:
    # 7 días siempre (enabled false, timeSlots vacío)
    return HospitalAvailabilityOut(
        id_hospital=hospital_id,
        days=[{"day": d, "enabled": False, "timeSlots": []} for d in WEEK_DAYS],
    )


def save_hospital_availability_service(
    hospital_id: str, body: HospitalAvailabilityIn
) -> HospitalAvailabilityOut:
    # 🔒 no confiamos en lo que venga del front para id_hospital
    payload = body.model_dump()
    payload["id_hospital"] = hospital_id  # fuente de verdad = token uid

    db.collection(AVAILABILITY_COLL).document(hospital_id).set(payload, merge=False)

    # devolvemos lo que guardamos (con id_hospital del uid)
    return HospitalAvailabilityOut(**payload)


def get_hospital_availability_service(hospital_id: str) -> HospitalAvailabilityOut:
    doc = db.collection(AVAILABILITY_COLL).document(hospital_id).get()

    if not doc.exists:
        return _default_availability(hospital_id)

    data = doc.to_dict() or {}

    # backstop: si falta algo, lo completamos para que SIEMPRE vuelvan 7 días
    existing_days = {
        d.get("day"): d
        for d in (data.get("days") or [])
        if isinstance(d, dict)
    }

    full_days = []
    for day_name in WEEK_DAYS:
        d = existing_days.get(day_name) or {"day": day_name, "enabled": False, "timeSlots": []}

        # normalizamos claves mínimas (por si hay docs viejos)
        full_days.append(
            {
                "day": d.get("day", day_name),
                "enabled": bool(d.get("enabled", False)),
                "timeSlots": d.get("timeSlots") or [],
            }
        )

    data["id_hospital"] = hospital_id
    data["days"] = full_days

    return HospitalAvailabilityOut(**data)
