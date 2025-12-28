from app.firebase.firebase_client import db
from app.schemas.appointment_schema import AppointmentCreate, RescheduleAppointmentRequest

def get_appointments_service(hospital_id: str):
    docs = (
        db.collection("appointments")
        .where("hospital_id", "==", hospital_id)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)

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

    data["hospital_id"] = hospital_id
    data["source"] = "HOSPITAL_MANUAL"
    data["status"] = "SCHEDULED"

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