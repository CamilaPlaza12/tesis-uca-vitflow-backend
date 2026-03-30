from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.firebase.firebase_client import db
from app.api.v1.services.donor_service import get_donor_by_dni_service
from app.api.v1.services.donor_eligibility_service import evaluate_donor_eligibility_service
from app.utils.blood_compatibility import can_donate_to_request
from app.utils.distance import haversine_km

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
HOSPITALS_COLLECTION = "hospitals"
HOSPITAL_REQUESTS_COLLECTION = "hospital_requests"


def _parse_iso_datetime(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BA_TZ)
        return dt
    except Exception:
        return None


def _build_request_item(req: dict, hospital: dict, distance_km: float | None):
    return {
        "request_id": req["id"],
        "hospital_id": req["hospital_id"],
        "hospital_name": hospital.get("name"),
        "hospital_address": hospital.get("address"),
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "blood_group": req.get("blood_group"),
        "component": req.get("component"),
        "priority": req.get("priority"),
        "hospital_unit": req.get("hospital_unit"),
        "requested_by": req.get("requested_by"),
        "comments": req.get("comments"),
        "request_type": req.get("request_type", "NORMAL"),
        "end_date": req.get("end_date"),
    }


def _get_active_requests():
    docs = (
        db.collection(HOSPITAL_REQUESTS_COLLECTION)
        .where("status", "==", "ACTIVO")
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)
    return results


def _get_hospital(hospital_id: str):
    snap = db.collection(HOSPITALS_COLLECTION).document(hospital_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data["id"] = snap.id
    return data


def get_nearby_donation_opportunities_for_donor_service(dni: str, radius_km: float = 5.0):
    donor = get_donor_by_dni_service(dni)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    donor_id = donor.get("id")
    evaluation = evaluate_donor_eligibility_service(donor_id)
    donor_status = evaluation.get("status") if evaluation else donor.get("eligibility_status")

    if donor_status != "APT":
        return {
            "donor_id": donor_id,
            "dni": dni,
            "eligibility_status": donor_status,
            "total": 0,
            "requests": [],
        }

    donor_geo = donor.get("geo") or {}
    donor_lat = donor_geo.get("lat")
    donor_lng = donor_geo.get("lng")

    if donor_lat is None or donor_lng is None:
        raise HTTPException(status_code=409, detail="Donor has no geo coordinates")

    donor_bg = donor.get("blood_group")
    now_ba = datetime.now(BA_TZ)

    results = []
    for req in _get_active_requests():
        end_dt = _parse_iso_datetime(req.get("end_date"))
        if not end_dt or end_dt < now_ba:
            continue

        if not can_donate_to_request(donor_bg, req.get("blood_group"), req.get("component")):
            continue

        hospital = _get_hospital(req.get("hospital_id"))
        if not hospital:
            continue

        hospital_geo = hospital.get("geo") or {}
        hospital_lat = hospital_geo.get("lat")
        hospital_lng = hospital_geo.get("lng")

        if hospital_lat is None or hospital_lng is None:
            continue

        distance_km = haversine_km(
            float(donor_lat),
            float(donor_lng),
            float(hospital_lat),
            float(hospital_lng),
        )

        if distance_km > radius_km:
            continue

        results.append(_build_request_item(req, hospital, distance_km))

    results.sort(key=lambda x: x["distance_km"])

    return {
        "donor_id": donor_id,
        "dni": dni,
        "eligibility_status": donor_status,
        "total": len(results),
        "requests": results,
    }


def get_campaigns_for_donor_service(dni: str):
    donor = get_donor_by_dni_service(dni)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    donor_id = donor.get("id")
    evaluation = evaluate_donor_eligibility_service(donor_id)
    donor_status = evaluation.get("status") if evaluation else donor.get("eligibility_status")

    if donor_status != "APT":
        return {
            "donor_id": donor_id,
            "dni": dni,
            "eligibility_status": donor_status,
            "total": 0,
            "requests": [],
        }

    donor_geo = donor.get("geo") or {}
    donor_lat = donor_geo.get("lat")
    donor_lng = donor_geo.get("lng")
    donor_bg = donor.get("blood_group")
    now_ba = datetime.now(BA_TZ)

    results = []
    for req in _get_active_requests():
        end_dt = _parse_iso_datetime(req.get("end_date"))
        if not end_dt or end_dt < now_ba:
            continue

        if not can_donate_to_request(donor_bg, req.get("blood_group"), req.get("component")):
            continue

        hospital = _get_hospital(req.get("hospital_id"))
        if not hospital:
            continue

        distance_km = None
        hospital_geo = hospital.get("geo") or {}
        hospital_lat = hospital_geo.get("lat")
        hospital_lng = hospital_geo.get("lng")

        if donor_lat is not None and donor_lng is not None and hospital_lat is not None and hospital_lng is not None:
            distance_km = haversine_km(
                float(donor_lat),
                float(donor_lng),
                float(hospital_lat),
                float(hospital_lng),
            )

        results.append(_build_request_item(req, hospital, distance_km))

    results.sort(
        key=lambda x: (
            x["distance_km"] is None,
            x["distance_km"] if x["distance_km"] is not None else 999999,
        )
    )

    return {
        "donor_id": donor_id,
        "dni": dni,
        "eligibility_status": donor_status,
        "total": len(results),
        "requests": results,
    }