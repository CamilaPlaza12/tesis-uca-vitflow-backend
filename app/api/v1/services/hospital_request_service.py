from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.firebase.firebase_client import db
from app.schemas.hospital_request_schema import HospitalRequestCreate

COLLECTION = "hospital_requests"
BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def create_hospital_request_service(
    hospital_id: str,
    body: HospitalRequestCreate,
    now_ba_iso: str,
    normalized_blood_group: str,
    normalized_component: str,
):
    data = body.model_dump()

    data["hospital_id"] = hospital_id
    data["datetime_local"] = now_ba_iso
    data["status"] = "ACTIVO"
    data["collected_units"] = 0
    data["blood_group"] = normalized_blood_group
    data["component"] = normalized_component
    data["request_type"] = body.request_type

    res = db.collection(COLLECTION).add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

    return {"id": doc_ref.id, **data}


def get_hospital_requests_service(hospital_id: str):
    docs = (
        db.collection(COLLECTION)
        .where("hospital_id", "==", hospital_id)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)

    results.sort(key=lambda x: x.get("datetime_local", ""), reverse=True)
    return results


def get_hospital_request_by_id_service(hospital_id: str, request_id: str):
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}

    if data.get("hospital_id") != hospital_id:
        return None

    data["id"] = snap.id
    return data


def get_hospital_request_any_service(request_id: str):
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    data["id"] = snap.id
    return data


def update_hospital_request_service(hospital_id: str, request_id: str, patch: dict):
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    patch.pop("requested_units", None)
    patch.pop("collected_units", None)

    doc_ref.update(patch)

    updated = {**data, **patch}
    updated["id"] = request_id
    return updated


def find_active_auto_request_by_blood_group_service(hospital_id: str, blood_group: str):
    docs = (
        db.collection(COLLECTION)
        .where("hospital_id", "==", hospital_id)
        .where("status", "==", "ACTIVO")
        .where("blood_group", "==", blood_group)
        .where("requested_by", "==", "Sistema")
        .limit(1)
        .stream()
    )

    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    return None


def create_auto_low_stock_request_service(hospital_id: str, blood_group: str, requested_units: float = 1.0):
    now_dt = datetime.now(BA_TZ)
    now_iso = now_dt.isoformat()
    end_date = (now_dt + timedelta(days=7)).isoformat()

    data = {
        "hospital_id": hospital_id,
        "datetime_local": now_iso,
        "hospital_unit": "Guardia",
        "component": "SANGRE",
        "blood_group": blood_group,
        "requested_units": float(requested_units),
        "collected_units": 0,
        "priority": "URGENTE",
        "status": "ACTIVO",
        "requested_by": "Sistema",
        "comments": "Pedido automático por bajo stock",
        "request_type": "NORMAL",
        "end_date": end_date,
    }

    res = db.collection(COLLECTION).add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res
    return {"id": doc_ref.id, **data}