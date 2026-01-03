from app.firebase.firebase_client import db
from app.schemas.hospital_request_schema import HospitalRequestCreate

COLLECTION = "hospital_requests"

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
    data["collected_liters"] = 0
    data["blood_group"] = normalized_blood_group
    data["component"] = normalized_component


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

def update_hospital_request_service(hospital_id: str, request_id: str, patch: dict):
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    patch.pop("requested_liters", None)
    patch.pop("collected_liters", None)

    doc_ref.update(patch)

    updated = {**data, **patch}
    updated["id"] = request_id
    return updated

