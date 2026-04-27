from datetime import datetime, date

from fastapi import HTTPException

from app.firebase.firebase_client import db
from app.schemas.appointment_schema import AppointmentCreate, AppointmentCreateFromVito, RescheduleAppointmentRequest
from app.api.v1.services.available_slots_service import reserve_slot_service, release_slot_service

HOSPITALS_COLLECTION = "hospitals"
ACTIVE_APPOINTMENT_STATUSES = {"PROGRAMADO", "CONFIRMADO"}


def _get_hospital_name(hospital_id: str | None) -> str | None:
    hospital_id = (hospital_id or "").strip()
    if not hospital_id:
        return None

    snap = db.collection(HOSPITALS_COLLECTION).document(hospital_id).get()
    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    return data.get("name")


def get_appointments_service(hospital_id: str):
    docs = (
        db.collection("appointments")
        .where("hospital_id", "==", hospital_id)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)

    results.sort(key=lambda x: (x.get("date_local", ""), x.get("time_local", "")))
    return results


def get_appointment_by_id_service(hospital_id: str, appointment_id: str):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        return None

    data["id"] = snap.id
    return data


def get_appointment_any_by_id_service(appointment_id: str):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    data["id"] = snap.id
    return data


def donor_has_active_appointment_service(donor_id: str, donor_dni: str | None = None) -> bool:
    donor_id = (donor_id or "").strip()
    donor_dni = (donor_dni or "").strip()

    if donor_id:
        docs = (
            db.collection("appointments")
            .where("donor_id", "==", donor_id)
            .stream()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            if data.get("status") in ACTIVE_APPOINTMENT_STATUSES:
                return True

    if donor_dni:
        docs = (
            db.collection("appointments")
            .where("donor.dni", "==", donor_dni)
            .stream()
        )
        for doc in docs:
            data = doc.to_dict() or {}
            if data.get("status") in ACTIVE_APPOINTMENT_STATUSES:
                return True

    return False


def get_active_appointment_by_dni_service(dni: str):
    normalized_dni = (dni or "").strip()
    if not normalized_dni:
        return None

    docs = (
        db.collection("appointments")
        .where("donor.dni", "==", normalized_dni)
        .stream()
    )

    candidates = []
    for doc in docs:
        data = doc.to_dict() or {}
        if data.get("status") not in ACTIVE_APPOINTMENT_STATUSES:
            continue

        data["id"] = doc.id
        data["hospital_name"] = _get_hospital_name(data.get("hospital_id"))
        candidates.append(data)

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x.get("date_local", ""), x.get("time_local", "")))
    return candidates[0]


def create_appointment_manual_service(hospital_id: str, appointment: AppointmentCreate):
    data = appointment.model_dump()

    slot_key = reserve_slot_service(hospital_id, appointment.date_local, appointment.time_local)

    data["hospital_id"] = hospital_id
    data["source"] = "HOSPITAL_MANUAL"
    data["status"] = "PROGRAMADO"
    data["slot_key"] = slot_key

    if data.get("date_local") is not None:
        data["date_local"] = data["date_local"].isoformat()

    res = db.collection("appointments").add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

    return {"id": doc_ref.id, **data}


def create_appointment_from_vito_service(
    hospital_id: str,
    appointment: AppointmentCreateFromVito,
    donor: dict,
    donation_type: str,
):
    full_name = f"{(donor.get('first_name') or '').strip()} {(donor.get('last_name') or '').strip()}".strip()
    if not full_name:
        raise HTTPException(status_code=409, detail="Donor full_name is required")

    slot_key = reserve_slot_service(hospital_id, appointment.date_local, appointment.time_local)

    data = {
        "donor_id": appointment.donor_id,
        "hospital_request_id": appointment.hospital_request_id,
        "date_local": appointment.date_local.isoformat(),
        "time_local": appointment.time_local,
        "donor": {
            "full_name": full_name,
            "dni": donor.get("dni"),
        },
        "donation_type": donation_type,
        "hospital_id": hospital_id,
        "source": "VITO_WHATSAPP",
        "status": "PROGRAMADO",
        "slot_key": slot_key,
    }

    res = db.collection("appointments").add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

    return {"id": doc_ref.id, **data}


def update_appointment_status_service(hospital_id: str, appointment_id: str, new_status: str):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        return None

    doc_ref.update({"status": new_status})
    data["status"] = new_status
    data["id"] = appointment_id
    return data


def update_appointment_status_any_service(appointment_id: str, new_status: str):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    doc_ref.update({"status": new_status})
    data["status"] = new_status
    data["id"] = appointment_id
    return data


def reschedule_appointment_service(
    hospital_id: str,
    appointment_id: str,
    body: RescheduleAppointmentRequest,
):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        return None

    new_date_str = body.date_local.isoformat()
    new_time_str = body.time_local

    doc_ref.update({
        "date_local": new_date_str,
        "time_local": new_time_str,
    })

    data["date_local"] = new_date_str
    data["time_local"] = new_time_str
    data["id"] = appointment_id
    return data


def reschedule_appointment_with_slots_service(
    hospital_id: str,
    appointment_id: str,
    body: RescheduleAppointmentRequest,
):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        return None

    old_date_str = data.get("date_local")
    old_time_str = data.get("time_local")

    if not old_date_str or not old_time_str:
        raise HTTPException(status_code=409, detail="Appointment has no date/time to reschedule")

    old_date = datetime.fromisoformat(old_date_str).date()
    new_date = body.date_local
    new_time = body.time_local

    new_slot_key = reserve_slot_service(hospital_id, new_date, new_time)

    try:
        release_slot_service(hospital_id, old_date, old_time_str)
        doc_ref.update({
            "date_local": new_date.isoformat(),
            "time_local": new_time,
            "slot_key": new_slot_key,
        })
    except Exception:
        try:
            release_slot_service(hospital_id, new_date, new_time)
        except Exception:
            pass
        raise

    data["date_local"] = new_date.isoformat()
    data["time_local"] = new_time
    data["slot_key"] = new_slot_key
    data["id"] = appointment_id
    return data


def reschedule_appointment_any_with_slots_service(
    appointment_id: str,
    body: RescheduleAppointmentRequest,
):
    doc_ref = db.collection("appointments").document(appointment_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    data = snap.to_dict() or {}

    hospital_id = data.get("hospital_id")
    if not hospital_id:
        raise HTTPException(status_code=409, detail="Appointment has no hospital_id")

    old_date_str = data.get("date_local")
    old_time_str = data.get("time_local")

    if not old_date_str or not old_time_str:
        raise HTTPException(status_code=409, detail="Appointment has no date/time to reschedule")

    old_date = datetime.fromisoformat(old_date_str).date()
    new_date = body.date_local
    new_time = body.time_local

    new_slot_key = reserve_slot_service(hospital_id, new_date, new_time)

    try:
        release_slot_service(hospital_id, old_date, old_time_str)
        doc_ref.update({
            "date_local": new_date.isoformat(),
            "time_local": new_time,
            "slot_key": new_slot_key,
        })
    except Exception:
        try:
            release_slot_service(hospital_id, new_date, new_time)
        except Exception:
            pass
        raise

    data["date_local"] = new_date.isoformat()
    data["time_local"] = new_time
    data["slot_key"] = new_slot_key
    data["id"] = appointment_id
    return data


def cancel_appointments_by_request_service(hospital_id: str, hospital_request_id: str) -> dict:
    docs = (
        db.collection("appointments")
        .where("hospital_id", "==", hospital_id)
        .where("hospital_request_id", "==", hospital_request_id)
        .stream()
    )

    cancelled = 0
    donor_ids: list[str] = []

    for snap in docs:
        appt = snap.to_dict() or {}
        appt_status = appt.get("status")

        if appt_status not in {"PROGRAMADO", "CONFIRMADO"}:
            continue

        date_str = appt.get("date_local")
        time_str = appt.get("time_local")

        if date_str and time_str:
            try:
                old_date = datetime.fromisoformat(date_str).date()
                release_slot_service(hospital_id, old_date, time_str)
            except Exception:
                raise HTTPException(status_code=409, detail="Failed to release slot for an appointment")

        snap.reference.update({"status": "CANCELADO"})
        cancelled += 1

        donor_id = appt.get("donor_id")
        if donor_id:
            donor_ids.append(donor_id)

    return {"cancelled_count": cancelled, "donor_ids": donor_ids}


def search_appointments_by_range_service(hospital_id: str, desde: date, hasta: date):
    desde_str = desde.isoformat()
    hasta_str = hasta.isoformat()

    q = (
        db.collection("appointments")
        .where("hospital_id", "==", hospital_id)
        .where("date_local", ">=", desde_str)
        .where("date_local", "<=", hasta_str)
        .order_by("date_local")
    )

    docs = q.stream()

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        results.append(data)

    return results