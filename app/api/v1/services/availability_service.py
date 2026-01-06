from app.schemas.availability_schema import AvailabilityOptions, ALLOWED_WEEKDAYS, ALLOWED_TIMES_LIST, HospitalAvailability
from app.firebase.firebase_client import db

def get_availability_options_service() -> AvailabilityOptions:
    return AvailabilityOptions(
        weekdays=ALLOWED_WEEKDAYS,
        times=ALLOWED_TIMES_LIST,
    )

def save_hospital_availability_service(hospital_id: str, body: HospitalAvailability) -> HospitalAvailability:
    payload = body.model_dump()
    payload["hospital_id"] = hospital_id
    db.collection("hospital_availability").document(hospital_id).set(payload, merge=False)
    return body

def get_hospital_availability_service(hospital_id: str) -> HospitalAvailability:
    doc = db.collection("hospital_availability").document(hospital_id).get()

    if not doc.exists:
        return HospitalAvailability(weekly={})

    data = doc.to_dict() or {}
    return HospitalAvailability(**data)
