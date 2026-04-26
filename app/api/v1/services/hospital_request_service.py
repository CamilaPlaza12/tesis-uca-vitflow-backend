from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.firebase.firebase_client import db
from app.schemas.hospital_request_schema import HospitalRequestCreate

COLLECTION = "hospital_requests"
BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

COMPONENTE_TO_REQUEST_COMPONENT = {
    "globulos_rojos": "SANGRE",
    "plaquetas": "PLAQUETAS",
    "plasma": "PLASMA",
}

ALL_BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]


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


def get_hospital_request_status_service(request_id: str) -> dict | None:
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    status = data.get("status", "")
    is_active = (status == "ACTIVO")

    return {
        "request_id": request_id,
        "is_active": is_active,
        "status": status,
    }


def update_hospital_request_service(hospital_id: str, request_id: str, patch: dict):
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    patch.pop("requested_units", None)

    doc_ref.update(patch)

    updated = {**data, **patch}
    updated["id"] = request_id
    return updated


def find_active_auto_request_by_blood_group_service(hospital_id: str, blood_group: str, componente: str):
    request_component = COMPONENTE_TO_REQUEST_COMPONENT.get(componente, componente.upper())
    docs = (
        db.collection(COLLECTION)
        .where("hospital_id", "==", hospital_id)
        .where("status", "==", "ACTIVO")
        .where("blood_group", "==", blood_group)
        .where("component", "==", request_component)
        .where("requested_by", "==", "Sistema")
        .limit(1)
        .stream()
    )

    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    return None


def create_auto_low_stock_request_service(hospital_id: str, blood_group: str, componente: str):
    now_dt = datetime.now(BA_TZ)
    now_iso = now_dt.isoformat()
    end_date = (now_dt + timedelta(days=5)).isoformat()
    request_component = COMPONENTE_TO_REQUEST_COMPONENT.get(componente, componente.upper())

    data = {
        "hospital_id": hospital_id,
        "datetime_local": now_iso,
        "hospital_unit": "Guardia",
        "component": request_component,
        "blood_group": blood_group,
        "priority": "URGENTE",
        "status": "ACTIVO",
        "requested_by": "Sistema",
        "comments": f"Pedido automático por bajo stock de {request_component}",
        "request_type": "NORMAL",
        "tipo": "automatico",
        "end_date": end_date,
    }

    res = db.collection(COLLECTION).add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res
    return {"id": doc_ref.id, **data}


def process_expired_auto_requests_service(hospital_id: str, blood_group: str, componente: str):
    """
    Cierra (FINALIZADO) los pedidos automáticos ACTIVOS vencidos para ese blood_group + componente.
    Retorna cuántos se cerraron.
    """
    now_dt = datetime.now(BA_TZ)
    request_component = COMPONENTE_TO_REQUEST_COMPONENT.get(componente, componente.upper())

    docs = (
        db.collection(COLLECTION)
        .where("hospital_id", "==", hospital_id)
        .where("status", "==", "ACTIVO")
        .where("blood_group", "==", blood_group)
        .where("component", "==", request_component)
        .where("requested_by", "==", "Sistema")
        .stream()
    )

    closed = 0
    for doc in docs:
        data = doc.to_dict() or {}
        end_date_str = data.get("end_date", "")
        if not end_date_str:
            continue
        try:
            end_dt = datetime.fromisoformat(end_date_str)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=BA_TZ)
        except Exception:
            continue

        if end_dt < now_dt:
            doc.reference.update({"status": "FINALIZADO"})
            closed += 1

    return closed


def find_active_manual_request_service(hospital_id: str, blood_group: str, component: str):
    docs = (
        db.collection(COLLECTION)
        .where("hospital_id", "==", hospital_id)
        .where("status", "==", "ACTIVO")
        .where("blood_group", "==", blood_group)
        .where("component", "==", component)
        .where("tipo", "==", "manual")
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data
    return None


def get_available_blood_groups_service(hospital_id: str, component: str) -> dict:
    docs = (
        db.collection(COLLECTION)
        .where("hospital_id", "==", hospital_id)
        .where("status", "==", "ACTIVO")
        .where("component", "==", component)
        .where("tipo", "==", "manual")
        .stream()
    )
    occupied = {(doc.to_dict() or {}).get("blood_group", "") for doc in docs}
    disponibles = [bg for bg in ALL_BLOOD_GROUPS if bg not in occupied]
    no_disponibles = [bg for bg in ALL_BLOOD_GROUPS if bg in occupied]
    return {"disponibles": disponibles, "no_disponibles": no_disponibles}