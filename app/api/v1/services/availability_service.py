from app.schemas.availability_schema import HospitalAvailability
from app.firebase.firebase_client import db

AVAILABILITY_COLL = "hospital_availability"

def save_hospital_availability_service(
    hospital_id: str, body: HospitalAvailability
) -> HospitalAvailability:
    payload = body.model_dump()
    payload["hospital_id"] = hospital_id
    db.collection(AVAILABILITY_COLL).document(hospital_id).set(payload, merge=False)
    return body

def get_hospital_availability_service(
    hospital_id: str,
) -> HospitalAvailability:
    doc = db.collection(AVAILABILITY_COLL).document(hospital_id).get()

    if not doc.exists:
        return HospitalAvailability(weekly={})

    data = doc.to_dict() or {}
    return HospitalAvailability(**data)
