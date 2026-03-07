from datetime import date
from app.firebase.firebase_client import db
from app.schemas.donor_schema import DonorCreate
from app.utils.geocoding import geocode_address_nominatim
from app.utils.age import compute_age_years

COLLECTION = "donors"


def _attach_age(donor_dict: dict) -> dict:
    try:
        y, m, d = donor_dict["birth_date"].split("-")
        bd = date(int(y), int(m), int(d))
        donor_dict["age_years"] = compute_age_years(bd, date.today())
    except Exception:
        donor_dict["age_years"] = 0
    return donor_dict


def _with_defaults(donor_dict: dict) -> dict:
    donor_dict.setdefault("medications", [])
    donor_dict.setdefault("has_recent_tattoo", False)
    donor_dict.setdefault("last_donation_date", None)
    donor_dict.setdefault("is_pregnant", None)
    donor_dict.setdefault("has_fever_or_infection", False)
    donor_dict.setdefault("screening_updated_at", None)

    donor_dict.setdefault("eligibility_status", None)
    donor_dict.setdefault("eligibility_available_from", None)
    donor_dict.setdefault("eligibility_checked_at", None)
    donor_dict.setdefault("eligibility_reasons", [])

    return donor_dict


def get_donor_by_id_service(donor_id: str):
    snap = db.collection(COLLECTION).document(donor_id).get()
    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    data["id"] = snap.id
    data = _with_defaults(data)
    return _attach_age(data)


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
        data = _with_defaults(data)
        return _attach_age(data)
    return None


def get_all_donors_service():
    docs = db.collection(COLLECTION).stream()
    donors = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        data = _with_defaults(data)
        donors.append(_attach_age(data))
    return donors


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
        data = _with_defaults(data)
        donors.append(_attach_age(data))
    return donors


def create_donor_service(body: DonorCreate):
    existing = get_donor_by_dni_service(body.dni)
    if existing:
        return {"_error": "DNI_ALREADY_EXISTS", "existing_id": existing["id"]}

    data = body.model_dump()
    geo = geocode_address_nominatim(data["address_text"])
    if geo is None:
        return {"_error": "GEOCODE_FAILED"}

    data["geo"] = geo
    data["eligibility_status"] = None
    data["eligibility_available_from"] = None
    data["eligibility_checked_at"] = None
    data["eligibility_reasons"] = []

    res = db.collection(COLLECTION).add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

    out = {"id": doc_ref.id, **data}
    out = _with_defaults(out)
    return _attach_age(out)


def update_donor_service(donor_id: str, patch: dict):
    doc_ref = db.collection(COLLECTION).document(donor_id)
    snap = doc_ref.get()
    if not snap.exists:
        return None

    existing = snap.to_dict() or {}

    if "address_text" in patch:
        geo = geocode_address_nominatim(patch["address_text"])
        if geo is None:
            return {"_error": "GEOCODE_FAILED"}
        patch["geo"] = geo

    doc_ref.update(patch)

    updated = {**existing, **patch}
    updated["id"] = donor_id
    updated = _with_defaults(updated)
    return _attach_age(updated)