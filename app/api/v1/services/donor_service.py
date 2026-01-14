from app.firebase.firebase_client import db
from app.schemas.donor_schema import DonorCreate
from app.utils.geocoding import geocode_address_nominatim

COLLECTION = "donors"

def get_donor_by_id_service(donor_id: str):
    snap = db.collection(COLLECTION).document(donor_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    data["id"] = snap.id
    return data

def get_all_donors_service():
    docs = db.collection(COLLECTION).stream()
    donors = []

    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        donors.append(data)

    return donors

def get_donor_by_dni_service(dni: str):
    docs = (
        db.collection(COLLECTION)
        .where("dni", "==", dni)
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data
    return None


def create_donor_service(body: DonorCreate, now_ba_iso: str):
    existing = get_donor_by_dni_service(body.dni)
    if existing:
        return {"_error": "DNI_ALREADY_EXISTS", "existing_id": existing["id"]}

    data = body.model_dump()

    #Completar geo si no vino
    if data.get("geo") is None:
        geo = geocode_address_nominatim(data["address_text"])
        if geo is None:
            return {"_error": "GEOCODE_FAILED"}
        data["geo"] = geo

    data["created_at_local"] = now_ba_iso
    data["updated_at_local"] = None

    res = db.collection(COLLECTION).add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

    return {"id": doc_ref.id, **data}

def update_donor_service(donor_id: str, patch: dict, now_ba_iso: str):
    doc_ref = db.collection(COLLECTION).document(donor_id)
    snap = doc_ref.get()
    if not snap.exists:
        return None

    existing = snap.to_dict() or {}

    #Si cambian address_text, recalculamos geo
    if "address_text" in patch and "geo" not in patch:
        geo = geocode_address_nominatim(patch["address_text"])
        if geo is None:
            return {"_error": "GEOCODE_FAILED"}
        patch["geo"] = geo

    patch["updated_at_local"] = now_ba_iso
    doc_ref.update(patch)

    updated = {**existing, **patch}
    updated["id"] = donor_id
    return updated


def get_donors_by_blood_group_service(blood_group: str):
    docs = (
        db.collection(COLLECTION)
        .where("blood_group", "==", blood_group)
        .stream()
    )

    donors = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        donors.append(data)

    return donors

