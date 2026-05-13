from datetime import date
import traceback

from app.firebase.firebase_client import db
from app.schemas.donor_schema import DonorCreate
from app.utils.geocoding import geocode_address_google
from app.utils.age import compute_age_years

COLLECTION = "donors"


def _attach_age(donor_dict: dict) -> dict:
    try:
        birth_date = donor_dict.get("birth_date")
        if birth_date:
            y, m, d = birth_date.split("-")
            bd = date(int(y), int(m), int(d))
            donor_dict["age_years"] = compute_age_years(bd, date.today())
        else:
            donor_dict["age_years"] = 0
    except Exception:
        print("[DONOR_SERVICE] ERROR en _attach_age")
        print("[DONOR_SERVICE] donor_dict =", donor_dict)
        traceback.print_exc()
        donor_dict["age_years"] = 0

    return donor_dict


def _with_defaults(donor_dict: dict) -> dict:
    donor_dict.setdefault("medications", [])
    donor_dict.setdefault("has_recent_tattoo", False)
    donor_dict.setdefault("last_tattoo_or_piercing_date", None)
    donor_dict.setdefault("last_donation_date", None)

    donor_dict.setdefault("is_pregnant", None)
    donor_dict.setdefault("is_currently_pregnant", None)
    donor_dict.setdefault("last_pregnancy_end_date", None)
    donor_dict.setdefault("pregnancy_end_type", None)
    donor_dict.setdefault("is_breastfeeding", None)

    donor_dict.setdefault("has_fever_or_infection", False)
    donor_dict.setdefault("has_active_fever_or_infection", None)
    donor_dict.setdefault("infection_resolved_date", None)

    donor_dict.setdefault("screening_updated_at", None)

    donor_dict.setdefault("eligibility_status", None)
    donor_dict.setdefault("eligibility_available_from", None)
    donor_dict.setdefault("eligibility_checked_at", None)
    donor_dict.setdefault("eligibility_reasons", [])

    donor_dict.setdefault("is_subscribed", True)
    donor_dict.setdefault("has_consent", True)
    donor_dict.setdefault("is_enabled", True)

    return donor_dict


def validate_address_service(address_text: str):
    try:
        print(f"[DONOR_SERVICE] validate_address_service address_text={address_text}")
        geo = geocode_address_google(address_text)
        if geo is None:
            print("[DONOR_SERVICE] validate_address_service -> geo None")
            return None

        return {
            "ok": True,
            "address_text": address_text,
            "geo": geo,
        }
    except Exception:
        print("[DONOR_SERVICE] ERROR en validate_address_service")
        traceback.print_exc()
        raise


def get_donor_by_id_service(donor_id: str):
    try:
        print(f"[DONOR_SERVICE] get_donor_by_id_service donor_id={donor_id}")

        snap = db.collection(COLLECTION).document(donor_id).get()
        if not snap.exists:
            print("[DONOR_SERVICE] donor no existe")
            return None

        data = snap.to_dict() or {}
        print("[DONOR_SERVICE] raw donor by id =", data)

        data["id"] = snap.id
        data = _with_defaults(data)
        data = _attach_age(data)

        print("[DONOR_SERVICE] final donor by id =", data)
        return data

    except Exception:
        print("[DONOR_SERVICE] ERROR en get_donor_by_id_service")
        traceback.print_exc()
        raise


def get_donor_by_dni_service(dni: str):
    try:
        print(f"[DONOR_SERVICE] get_donor_by_dni_service dni={dni}")

        docs = (
            db.collection(COLLECTION)
            .where("dni", "==", dni)
            .limit(1)
            .stream()
        )

        for doc in docs:
            data = doc.to_dict() or {}
            print("[DONOR_SERVICE] raw donor by dni =", data)

            data["id"] = doc.id
            data = _with_defaults(data)
            data = _attach_age(data)

            print("[DONOR_SERVICE] final donor by dni =", data)
            return data

        print("[DONOR_SERVICE] donor no encontrado por dni")
        return None

    except Exception:
        print("[DONOR_SERVICE] ERROR en get_donor_by_dni_service")
        traceback.print_exc()
        raise


def get_all_donors_service():
    try:
        print("[DONOR_SERVICE] get_all_donors_service")

        docs = db.collection(COLLECTION).stream()
        donors = []

        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            data = _with_defaults(data)
            data = _attach_age(data)
            donors.append(data)

        print(f"[DONOR_SERVICE] total donors={len(donors)}")
        return donors

    except Exception:
        print("[DONOR_SERVICE] ERROR en get_all_donors_service")
        traceback.print_exc()
        raise


def get_donors_by_blood_group_service(blood_group: str):
    try:
        print(f"[DONOR_SERVICE] get_donors_by_blood_group_service blood_group={blood_group}")

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
            data = _attach_age(data)

            if not data.get("is_enabled", True):
                continue

            donors.append(data)

        print(f"[DONOR_SERVICE] total donors blood_group={blood_group}: {len(donors)}")
        return donors

    except Exception:
        print("[DONOR_SERVICE] ERROR en get_donors_by_blood_group_service")
        traceback.print_exc()
        raise


def create_donor_service(body: DonorCreate):
    try:
        print(f"[DONOR_SERVICE] create_donor_service dni={body.dni}")

        existing = get_donor_by_dni_service(body.dni)
        if existing:
            return {"_error": "DNI_ALREADY_EXISTS", "existing_id": existing["id"]}

        data = body.model_dump()
        print("[DONOR_SERVICE] create payload =", data)

        geo = geocode_address_google(data["address_text"])
        if geo is None:
            return {"_error": "GEOCODE_FAILED"}

        data["geo"] = geo
        data["eligibility_status"] = None
        data["eligibility_available_from"] = None
        data["eligibility_checked_at"] = None
        data["eligibility_reasons"] = []
        data["is_enabled"] = True

        res = db.collection(COLLECTION).add(data)
        doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

        out = {"id": doc_ref.id, **data}
        out = _with_defaults(out)
        out = _attach_age(out)

        print("[DONOR_SERVICE] donor creado =", out)
        return out

    except Exception:
        print("[DONOR_SERVICE] ERROR en create_donor_service")
        traceback.print_exc()
        raise


def update_donor_last_donation_date_service(donor_id: str, donation_date: str):
    try:
        doc_ref = db.collection(COLLECTION).document(donor_id)
        snap = doc_ref.get()
        if not snap.exists:
            return
        doc_ref.update({
            "last_donation_date": donation_date,
            "eligibility_status": None,
            "eligibility_checked_at": None,
        })
    except Exception:
        print(f"[DONOR_SERVICE] ERROR en update_donor_last_donation_date_service donor_id={donor_id}")
        traceback.print_exc()


def update_donor_service(donor_id: str, patch: dict):
    try:
        print(f"[DONOR_SERVICE] update_donor_service donor_id={donor_id}")
        print("[DONOR_SERVICE] patch =", patch)

        doc_ref = db.collection(COLLECTION).document(donor_id)
        snap = doc_ref.get()
        if not snap.exists:
            print("[DONOR_SERVICE] donor no existe para update")
            return None

        existing = snap.to_dict() or {}

        if "address_text" in patch:
            geo = geocode_address_google(patch["address_text"])
            if geo is None:
                return {"_error": "GEOCODE_FAILED"}
            patch["geo"] = geo

        doc_ref.update(patch)

        updated = {**existing, **patch}
        updated["id"] = donor_id
        updated = _with_defaults(updated)
        updated = _attach_age(updated)

        print("[DONOR_SERVICE] donor actualizado =", updated)
        return updated

    except Exception:
        print("[DONOR_SERVICE] ERROR en update_donor_service")
        traceback.print_exc()
        raise