import logging

from fastapi import HTTPException
from app.firebase.firebase_client import db
from app.utils.distance import haversine_km
from app.utils.blood_compatibility import can_donate_to_request

logger = logging.getLogger("vitflow.nearby_donors")

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
    component = (req.get("component") or "SANGRE").strip().upper()
    if not blood_group:
        raise HTTPException(status_code=409, detail="HospitalRequest has no blood_group")

    logger.info(
        "[NEARBY] Buscando donantes para request_id=%s blood_group=%s component=%s radius_km=%s",
        request_id, blood_group, component, radius_km,
    )

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

    # 3) traer TODOS los donors y filtrar por compatibilidad
    donor_docs = list(db.collection(DONORS_COLLECTION).stream())

    logger.info(
        "[NEARBY] Total donors en Firestore: %d — filtrando para blood_group=%s component=%s radius_km=%s",
        len(donor_docs), blood_group, component, radius_km,
    )

    donors = []

    for snap in donor_docs:
        donor = snap.to_dict() or {}
        donor_id = snap.id
        nombre = f"{donor.get('first_name', '')} {donor.get('last_name', '')}".strip()
        donor_bg = (donor.get("blood_group") or "").strip().upper()

        logger.info(
            "[NEARBY]   Evaluando id=%s nombre='%s' blood_group=%s eligibility=%s has_consent=%s is_subscribed=%s geo=%s",
            donor_id, nombre, donor_bg,
            donor.get("eligibility_status"),
            donor.get("has_consent"),
            donor.get("is_subscribed"),
            bool(donor.get("geo")),
        )

        if not can_donate_to_request(donor_bg, blood_group, component):
            logger.info(
                "[NEARBY]   → EXCLUIDO (incompatible: %s no puede donar a %s/%s)",
                donor_bg, blood_group, component,
            )
            continue

        donor_geo = donor.get("geo") or {}
        lat = donor_geo.get("lat")
        lng = donor_geo.get("lng")

        if lat is None or lng is None:
            logger.info(
                "[NEARBY]   EXCLUIDO (sin geo) id=%s nombre='%s'",
                donor_id, nombre,
            )
            continue

        eligibility = donor.get("eligibility_status")
        if eligibility != "APT":
            logger.info(
                "[NEARBY]   EXCLUIDO (eligibility=%s) id=%s nombre='%s'",
                eligibility, donor_id, nombre,
            )
            continue

        if donor.get("has_consent") is not True:
            logger.info(
                "[NEARBY]   EXCLUIDO (has_consent=%s) id=%s nombre='%s'",
                donor.get("has_consent"), donor_id, nombre,
            )
            continue

        if donor.get("is_subscribed") is not True:
            logger.info(
                "[NEARBY]   EXCLUIDO (is_subscribed=%s) id=%s nombre='%s'",
                donor.get("is_subscribed"), donor_id, nombre,
            )
            continue

        distance_km = haversine_km(
            float(hospital_lat),
            float(hospital_lng),
            float(lat),
            float(lng),
        )

        if distance_km > radius_km:
            logger.info(
                "[NEARBY]   EXCLUIDO (fuera de radio: %.2f km) id=%s nombre='%s'",
                distance_km, donor_id, nombre,
            )
            continue

        logger.info(
            "[NEARBY]   INCLUIDO id=%s nombre='%s' blood_group=%s distancia=%.2f km",
            donor_id, nombre, donor_bg, distance_km,
        )
        donors.append(
            {
                "id": donor_id,
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

    logger.info(
        "[NEARBY] Resultado final — request_id=%s total_incluidos=%d",
        request_id, len(donors),
    )

    return {
        "hospital_request_id": request_id,
        "hospital_id": hospital_id,
        "blood_group": blood_group,
        "radius_km": radius_km,
        "total": len(donors),
        "donors": donors,
    }