from datetime import datetime, timedelta, timezone, date

from app.firebase.firebase_client import db

COLLECTION = "donors"
MIN_WEIGHT_KG = 50.0


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _add_months_safe(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1

    if month == 2:
        leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        last_day = 29 if leap else 28
    elif month in (4, 6, 9, 11):
        last_day = 30
    else:
        last_day = 31

    day = min(d.day, last_day)
    return date(year, month, day)


def _max_date(current: date | None, candidate: date | None) -> date | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return max(current, candidate)


def evaluate_donor_eligibility_service(donor_id: str):
    doc_ref = db.collection(COLLECTION).document(donor_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    donor = snap.to_dict() or {}
    today = datetime.now(timezone.utc).date()

    hard_reasons = []
    wait_reasons = []
    available_from: date | None = None
    has_open_ended_wait = False

    weight_kg = donor.get("weight_kg")
    gender = donor.get("gender")

    last_donation_date = _parse_iso_date(donor.get("last_donation_date"))
    last_tattoo_or_piercing_date = _parse_iso_date(
        donor.get("last_tattoo_or_piercing_date")
    )

    is_currently_pregnant = donor.get("is_currently_pregnant")
    if is_currently_pregnant is None:
        is_currently_pregnant = donor.get("is_pregnant")

    last_pregnancy_end_date = _parse_iso_date(donor.get("last_pregnancy_end_date"))
    pregnancy_end_type = donor.get("pregnancy_end_type")
    is_breastfeeding = donor.get("is_breastfeeding")

    has_active_fever_or_infection = donor.get("has_active_fever_or_infection")
    if has_active_fever_or_infection is None:
        has_active_fever_or_infection = donor.get("has_fever_or_infection", False)

    infection_resolved_date = _parse_iso_date(donor.get("infection_resolved_date"))

    if weight_kg is None or weight_kg < MIN_WEIGHT_KG:
        hard_reasons.append("LOW_WEIGHT")

    if last_donation_date:
        next_available = _add_months_safe(last_donation_date, 2)
        if next_available > today:
            wait_reasons.append("RECENT_DONATION")
            available_from = _max_date(available_from, next_available)

    if last_tattoo_or_piercing_date:
        next_available = _add_months_safe(last_tattoo_or_piercing_date, 12)
        if next_available > today:
            wait_reasons.append("RECENT_TATTOO_OR_PIERCING")
            available_from = _max_date(available_from, next_available)
    elif donor.get("has_recent_tattoo") is True:
        wait_reasons.append("RECENT_TATTOO_OR_PIERCING")
        has_open_ended_wait = True

    if gender == "F" and is_currently_pregnant is True:
        wait_reasons.append("CURRENT_PREGNANCY")
        has_open_ended_wait = True

    if gender == "F" and last_pregnancy_end_date and pregnancy_end_type:
        if pregnancy_end_type == "VAGINAL_BIRTH":
            next_available = _add_months_safe(last_pregnancy_end_date, 2)
        elif pregnancy_end_type in {"CESAREAN", "NON_SPONTANEOUS_ABORTION"}:
            next_available = _add_months_safe(last_pregnancy_end_date, 12)
        else:
            next_available = None

        if next_available and next_available > today:
            wait_reasons.append("RECENT_PREGNANCY_EVENT")
            available_from = _max_date(available_from, next_available)

    if gender == "F" and is_breastfeeding is True:
        wait_reasons.append("BREASTFEEDING")
        has_open_ended_wait = True

    if has_active_fever_or_infection is True:
        wait_reasons.append("ACTIVE_FEVER_OR_INFECTION")
        has_open_ended_wait = True

    if infection_resolved_date:
        next_available = infection_resolved_date + timedelta(days=14)
        if next_available > today:
            wait_reasons.append("RECENT_FEVER_OR_INFECTION")
            available_from = _max_date(available_from, next_available)

    if hard_reasons:
        status = "NOT_APT"
    elif wait_reasons:
        status = "WAIT"
    else:
        status = "APT"

    if has_open_ended_wait:
        available_from = None

    reasons = hard_reasons + wait_reasons

    payload = {
        "eligibility_status": status,
        "eligibility_available_from": available_from.isoformat() if available_from else None,
        "eligibility_checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "eligibility_reasons": reasons,
    }

    doc_ref.update(payload)

    return {
        "donor_id": donor_id,
        "status": status,
        "available_from": payload["eligibility_available_from"],
        "reasons": reasons,
        **payload,
    }