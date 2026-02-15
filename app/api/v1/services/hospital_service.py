from datetime import datetime
from app.firebase.firebase_client import db

COLLECTION = "hospitals"


def create_hospital_from_onboarding_request(
    request_id: str,
    req: dict,
) -> str:
    now = datetime.utcnow().isoformat()

    hospital = req.get("hospital", {})
    address = hospital.get("address", {})

    if not hospital.get("name"):
        raise Exception("Hospital name missing in onboarding request")

    hospital_data = {
        "name": hospital.get("name"),
        "email": hospital.get("email"),
        "phone": hospital.get("phone"),
        "address": address,
        "subscriptionStatus": "PENDING_PAYMENT",
        "createdAt": now,
        "createdFromRequestId": request_id,
    }

    res = db.collection(COLLECTION).add(hospital_data)
    ref = res[1] if isinstance(res, (list, tuple)) else res

    return ref.id
