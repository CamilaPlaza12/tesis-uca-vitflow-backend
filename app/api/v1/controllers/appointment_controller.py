from fastapi import HTTPException, status
from datetime import datetime, time, date
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
    search_appointments_by_range_service,
    update_appointment_status_service,
    apply_completion_side_effects_service,
    reschedule_appointment_with_slots_service,
)
from app.api.v1.services.available_slots_service import release_slot_service
from app.api.v1.services.hospital_request_service import get_hospital_request_by_id_service

from app.utils.auth_utils import resolve_hospital_id

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

MIN_TIME = time(7, 0)
MAX_TIME = time(20, 0)


def get_appointments_controller(current_user: dict):
    hospital_id = resolve_hospital_id(current_user)
    return get_appointments_service(hospital_id)


def get_appointment_by_id_controller(appointment_id: str, current_user: dict):
    hospital_id = resolve_hospital_id(current_user)
    print("=== get_appointment_by_id_controller ===")
    print("hospital_id resuelto:", hospital_id)
    print("appointment_id:", repr(appointment_id))
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
    hospital_id = resolve_hospital_id(current_user)

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

    if t.minute % 5 != 0:
        raise HTTPException(
            status_code=400,
            detail="time_local must be in 5-minute intervals (00, 05, 10, ..., 55)",
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
    hospital_id = resolve_hospital_id(current_user)

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

    if new_status == "CANCELADO" and current_status in {"PROGRAMADO", "CONFIRMADO"}:
        date_str = existing.get("date_local")
        time_str = existing.get("time_local")
        if date_str and time_str:
            old_date = datetime.fromisoformat(date_str).date()
            release_slot_service(hospital_id, old_date, time_str)

    if new_status == "COMPLETADO" and current_status != "COMPLETADO":
        apply_completion_side_effects_service(hospital_id, updated)

    return updated


def reschedule_appointment_controller(appointment_id: str, body: RescheduleAppointmentRequest, current_user: dict):
    hospital_id = resolve_hospital_id(current_user)

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

    if t.minute % 5 != 0:
        raise HTTPException(
            status_code=400,
            detail="time_local must be in 5-minute intervals (00, 05, 10, ..., 55)",
        )

    now_ba = datetime.now(BA_TZ)
    new_dt_ba = datetime.combine(body.date_local, t).replace(tzinfo=BA_TZ)
    if new_dt_ba < now_ba:
        raise HTTPException(status_code=400, detail="Rescheduled datetime cannot be in the past")

    updated = reschedule_appointment_with_slots_service(hospital_id, appointment_id, body)
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return updated


MAX_RANGE_DAYS = 366


def search_appointments_by_range_controller(desde: date, hasta: date, current_user: dict):
    hospital_id = resolve_hospital_id(current_user)

    if desde > hasta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range: desde cannot be after hasta",
        )

    if (hasta - desde).days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid range: date range cannot exceed 1 year",
        )

    return search_appointments_by_range_service(hospital_id, desde, hasta)


def _first_day_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)


def _last_day_of_month(d: date) -> date:
    next_month_first = _add_months(d, 1)
    return next_month_first.fromordinal(next_month_first.toordinal() - 1)


def get_month_window_appointments_controller(current_user: dict):
    hospital_id = resolve_hospital_id(current_user)

    today_ba = datetime.now(BA_TZ).date()
    current_month_first = _first_day_of_month(today_ba)

    desde = _add_months(current_month_first, -1)
    end_month_first = _add_months(current_month_first, 2)
    hasta = _last_day_of_month(end_month_first)

    return search_appointments_by_range_service(hospital_id, desde, hasta)