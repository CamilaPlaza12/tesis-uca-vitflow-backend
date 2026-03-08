from fastapi import HTTPException
from app.firebase.firebase_client import db
from app.utils.distance import haversine_km

HOSPITALS_COLLECTION = "hospitals"
HOSPITAL_REQUESTS_COLLECTION = "hospital_requests"
DONORS_COLLECTION = "donors"


def get_nearby_donors_for_request_service(
    hospital_id: str,
    request_id: str,
    radius_km: float = 5.0,
):
    # 1) buscar request
    req_ref = db.collection(HOSPITAL_REQUESTS_COLLECTION).document(request_id)
    req_snap = req_ref.get()

    if not req_snap.exists:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    req = req_snap.to_dict() or {}

    if req.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    blood_group = (req.get("blood_group") or "").strip().upper()
    if not blood_group:
        raise HTTPException(status_code=409, detail="HospitalRequest has no blood_group")

    # 2) buscar hospital
    hospital_ref = db.collection(HOSPITALS_COLLECTION).document(hospital_id)
    hospital_snap = hospital_ref.get()

    if not hospital_snap.exists:
        raise HTTPException(status_code=404, detail="Hospital not found")

    hospital = hospital_snap.to_dict() or {}
    hospital_geo = hospital.get("geo") or {}

    hospital_lat = hospital_geo.get("lat")
    hospital_lng = hospital_geo.get("lng")

    if hospital_lat is None or hospital_lng is None:
        raise HTTPException(status_code=409, detail="Hospital has no geo coordinates")

    # 3) traer donors del mismo blood group
    donor_docs = (
        db.collection(DONORS_COLLECTION)
        .where("blood_group", "==", blood_group)
        .stream()
    )

    donors = []

    for snap in donor_docs:
        donor = snap.to_dict() or {}
        donor_geo = donor.get("geo") or {}

        lat = donor_geo.get("lat")
        lng = donor_geo.get("lng")

        if lat is None or lng is None:
            continue

        # filtro opcional de elegibilidad / consentimiento / suscripción
        if donor.get("eligibility_status") not in {None, "APT"}:
            continue

        if donor.get("has_consent") is not True:
            continue

        if donor.get("is_subscribed") is not True:
            continue

        distance_km = haversine_km(
            float(hospital_lat),
            float(hospital_lng),
            float(lat),
            float(lng),
        )

        if distance_km <= radius_km:
            donors.append(
                {
                    "id": snap.id,
                    "first_name": donor.get("first_name"),
                    "last_name": donor.get("last_name"),
                    "dni": donor.get("dni"),
                    "email": donor.get("email"),
                    "phone_number": donor.get("phone_number"),
                    "blood_group": donor.get("blood_group"),
                    "eligibility_status": donor.get("eligibility_status"),
                    "distance_km": round(distance_km, 2),
                }
            )

    donors.sort(key=lambda d: d["distance_km"])

    return {
        "hospital_request_id": request_id,
        "hospital_id": hospital_id,
        "blood_group": blood_group,
        "radius_km": radius_km,
        "total": len(donors),
        "donors": donors,
    }