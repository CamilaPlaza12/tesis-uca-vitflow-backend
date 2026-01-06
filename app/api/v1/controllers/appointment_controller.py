from fastapi import HTTPException, status
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.schemas.appointment_schema import (
    AppointmentCreate,
    RescheduleAppointmentRequest,
    UpdateAppointmentStatusRequest,
)

from app.api.v1.services.appointment_service import (
    get_appointments_service,
    get_appointment_by_id_service,
    create_appointment_manual_service,
    update_appointment_status_service,
    reschedule_appointment_service,
    apply_completion_side_effects_service,
    reschedule_appointment_with_slots_service
)
from app.api.v1.services.available_slots_service import release_slot_service
from app.api.v1.services.hospital_request_service import get_hospital_request_by_id_service


BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

MIN_TIME = time(7, 0)
MAX_TIME = time(20, 0)


def get_appointments_controller(current_user: dict):
    hospital_id = current_user.get("uid")
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )
    return get_appointments_service(hospital_id)


def get_appointment_by_id_controller(appointment_id: str, current_user: dict):
    hospital_id = current_user.get("uid") if current_user else None
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

    if not appointment_id or not appointment_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="appointment_id is required",
        )

    appointment = get_appointment_by_id_service(hospital_id, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return appointment


def create_appointment_manual_controller(appointment: AppointmentCreate, current_user: dict):
    hospital_id = current_user.get("uid") if current_user else None
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

    req_id = appointment.hospital_request_id.strip()
    if not req_id:
        raise HTTPException(status_code=400, detail="hospital_request_id is required")

    hospital_request = get_hospital_request_by_id_service(hospital_id, req_id)
    if not hospital_request:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    if hospital_request.get("status") != "ACTIVO":
        raise HTTPException(
            status_code=409,
            detail="Cannot create appointment: HospitalRequest is not ACTIVO",
        )

    if not appointment.donor.full_name.strip():
        raise HTTPException(status_code=400, detail="Donor full_name is required")

    dni = appointment.donor.dni.strip()
    if not dni.isdigit():
        raise HTTPException(status_code=400, detail="Donor dni must contain only digits")

    try:
        hh, mm = appointment.time_local.split(":")
        t = time(int(hh), int(mm))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time_local format")

    if t < MIN_TIME or t > MAX_TIME:
        raise HTTPException(
            status_code=400,
            detail=f"time_local must be between {MIN_TIME.strftime('%H:%M')} and {MAX_TIME.strftime('%H:%M')}",
        )

    if t.minute % 15 != 0:
        raise HTTPException(
            status_code=400,
            detail="time_local must be in 15-minute intervals (00, 15, 30, 45)",
        )

    now_ba = datetime.now(BA_TZ)
    appt_dt_ba = datetime.combine(appointment.date_local, t).replace(tzinfo=BA_TZ)
    if appt_dt_ba < now_ba:
        raise HTTPException(status_code=400, detail="Appointment datetime cannot be in the past")

    return create_appointment_manual_service(hospital_id, appointment)


def _validate_status_transition(current_status: str, new_status: str):
    terminal = {"CANCELADO", "COMPLETADO", "NO_PRESENTADO"}
    if current_status in terminal:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change status from terminal state {current_status}",
        )

    allowed = {
        "PROGRAMADO": {"CONFIRMADO", "CANCELADO", "NO_PRESENTADO"},
        "CONFIRMADO": {"COMPLETADO", "CANCELADO", "NO_PRESENTADO"},
    }

    if current_status not in allowed:
        raise HTTPException(status_code=409, detail="Invalid current status")

    if new_status not in allowed[current_status]:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid status transition {current_status} -> {new_status}",
        )


def update_appointment_status_controller(appointment_id: str, body: UpdateAppointmentStatusRequest, current_user: dict):
    hospital_id = current_user.get("uid") if current_user else None
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

    if not appointment_id or not appointment_id.strip():
        raise HTTPException(status_code=400, detail="appointment_id is required")

    existing = get_appointment_by_id_service(hospital_id, appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    current_status = existing.get("status")
    new_status = body.status

    if current_status == new_status:
        return existing

    if not current_status:
        raise HTTPException(status_code=409, detail="Appointment has no status")

    _validate_status_transition(current_status, new_status)

    updated = update_appointment_status_service(hospital_id, appointment_id, new_status)
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # ✅ liberar cupo si se cancela (solo si antes ocupaba cupo)
    if new_status == "CANCELADO" and current_status in {"PROGRAMADO", "CONFIRMADO"}:
        date_str = existing.get("date_local")
        time_str = existing.get("time_local")
        if date_str and time_str:
            old_date = datetime.fromisoformat(date_str).date()
            release_slot_service(hospital_id, old_date, time_str)

    # ✅ Efectos automáticos cuando un turno se completa (una sola vez)
    if new_status == "COMPLETADO" and current_status != "COMPLETADO":
        apply_completion_side_effects_service(hospital_id, updated)

    return updated


def reschedule_appointment_controller(appointment_id: str, body: RescheduleAppointmentRequest, current_user: dict):
    hospital_id = current_user.get("uid") if current_user else None
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

    if not appointment_id or not appointment_id.strip():
        raise HTTPException(status_code=400, detail="appointment_id is required")

    existing = get_appointment_by_id_service(hospital_id, appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if existing.get("status") in {"CANCELADO", "COMPLETADO", "NO_PRESENTADO"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reschedule appointment in state {existing.get('status')}",
        )

    try:
        hh, mm = body.time_local.split(":")
        t = time(int(hh), int(mm))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time_local format")

    if t < MIN_TIME or t > MAX_TIME:
        raise HTTPException(
            status_code=400,
            detail=f"time_local must be between {MIN_TIME.strftime('%H:%M')} and {MAX_TIME.strftime('%H:%M')}",
        )

    if t.minute % 15 != 0:
        raise HTTPException(
            status_code=400,
            detail="time_local must be in 15-minute intervals (00, 15, 30, 45)",
        )

    now_ba = datetime.now(BA_TZ)
    new_dt_ba = datetime.combine(body.date_local, t).replace(tzinfo=BA_TZ)
    if new_dt_ba < now_ba:
        raise HTTPException(status_code=400, detail="Rescheduled datetime cannot be in the past")

    updated = reschedule_appointment_with_slots_service(hospital_id, appointment_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return updated
