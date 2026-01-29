from app.api.v1.services.available_slots_service import reserve_slot_service
from app.firebase.firebase_client import db
from app.schemas.appointment_schema import AppointmentCreate, RescheduleAppointmentRequest

from app.api.v1.services.hospital_request_service import get_hospital_request_by_id_service
from datetime import datetime
from app.api.v1.services.available_slots_service import reserve_slot_service, release_slot_service,build_slot_key
from app.api.v1.services.blood_bank_service import add_blood_ml_by_group_service


HOSPITAL_REQUESTS_COLLECTION = "hospital_requests"
DONATION_LITERS_PER_COMPLETED_APPOINTMENT = 0.45


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


def apply_completion_side_effects_service(hospital_id: str, appointment_data: dict):
    """
    Se llama SOLO cuando un turno transiciona a COMPLETADO por primera vez.
    - Suma 0.45 L al pedido asociado (por ahora fijo)
    - Si alcanza/supera requested => status del pedido pasa a COMPLETO automáticamente
    """
    req_id = (appointment_data.get("hospital_request_id") or "").strip()
    if not req_id:
        return

    hospital_request = get_hospital_request_by_id_service(hospital_id, req_id)
    if not hospital_request:
        return
    
    blood_group = (hospital_request.get("blood_group") or "").strip().upper()
    if blood_group:
        add_blood_ml_by_group_service(hospital_id, blood_group, 450)

    req_status = hospital_request.get("status")
    if req_status not in {"ACTIVO", "FINALIZADO"}:
        return

    collected = float(hospital_request.get("collected_liters", 0) or 0)
    requested = float(hospital_request.get("requested_liters", 0) or 0)

    print("Applying completion side effects: requested =", requested)

    new_collected = collected + DONATION_LITERS_PER_COMPLETED_APPOINTMENT

    new_collected = round(new_collected, 4)

    print("Applying completion side effects: new_collected =", new_collected)

    patch = {"collected_liters": new_collected}

    if requested > 0 and new_collected >= requested:
        patch["status"] = "COMPLETO"

    db.collection(HOSPITAL_REQUESTS_COLLECTION).document(req_id).update(patch)

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
        # 2) liberar cupo del slot viejo
        release_slot_service(hospital_id, old_date, old_time_str)

        # 3) update appointment
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


def cancel_appointments_by_request_service(hospital_id: str, hospital_request_id: str) -> int:
    """
    Cancela todos los appointments activos (PROGRAMADO/CONFIRMADO) asociados al pedido.
    Libera el cupo del slot si corresponde.
    Devuelve cantidad cancelada.
    """
    # Traemos appointments del hospital por request_id
    docs = (
        db.collection("appointments")
        .where("hospital_id", "==", hospital_id)
        .where("hospital_request_id", "==", hospital_request_id)
        .stream()
    )

    cancelled = 0

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

        # Update status
        snap.reference.update({"status": "CANCELADO"})
        cancelled += 1

    return cancelled

