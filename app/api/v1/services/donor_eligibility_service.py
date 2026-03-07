from datetime import datetime, timedelta, timezone

from app.firebase.firebase_client import db

COLLECTION = "donors"
MIN_WEIGHT_KG = 50.0
DONATION_WAIT_DAYS = 56


def _parse_iso_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def evaluate_donor_eligibility_service(donor_id: str):
    doc_ref = db.collection(COLLECTION).document(donor_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    donor = snap.to_dict() or {}
    today = datetime.now(timezone.utc).date()

    hard_reasons = []
    wait_reasons = []
    available_from = None

    weight_kg = donor.get("weight_kg")
    gender = donor.get("gender")
    is_pregnant = donor.get("is_pregnant")
    has_fever_or_infection = donor.get("has_fever_or_infection", False)
    has_recent_tattoo = donor.get("has_recent_tattoo", False)
    last_donation_date = donor.get("last_donation_date")

    if has_fever_or_infection is True:
        hard_reasons.append("FEVER_OR_INFECTION")

    if weight_kg is None or weight_kg < MIN_WEIGHT_KG:
        hard_reasons.append("LOW_WEIGHT")

    if gender == "F" and is_pregnant is True:
        hard_reasons.append("PREGNANCY_OR_RECENT_BIRTH")

    if has_recent_tattoo is True:
        wait_reasons.append("RECENT_TATTOO_OR_PIERCING")

    last_dt = _parse_iso_date(last_donation_date)
    if last_dt:
        next_available = last_dt + timedelta(days=DONATION_WAIT_DAYS)
        if next_available > today:
            wait_reasons.append("RECENT_DONATION")
            available_from = next_available.strftime("%Y-%m-%d")

    if hard_reasons:
        status = "NOT_APT"
    elif wait_reasons:
        status = "WAIT"
    else:
        status = "APT"

    reasons = hard_reasons + wait_reasons

    payload = {
        "eligibility_status": status,
        "eligibility_available_from": available_from,
        "eligibility_checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "eligibility_reasons": reasons,
    }

    doc_ref.update(payload)

    return {
        "donor_id": donor_id,
        "status": status,
        "available_from": available_from,
        "reasons": reasons,
        **payload,
    }