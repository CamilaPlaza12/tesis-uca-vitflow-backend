from datetime import datetime, time, date
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.schemas.appointment_schema import (
    AppointmentCreate,
    AppointmentCreateFromVito,
    ConfirmarAsistenciaRequest,
    ConfirmarAsistenciaOut,
    UnidadResumen,
    RescheduleAppointmentRequest,
    UpdateAppointmentStatusRequest,
)
from app.api.v1.services.appointment_service import (
    get_appointments_service,
    get_appointment_by_id_service,
    get_appointment_any_by_id_service,
    create_appointment_manual_service,
    create_appointment_from_vito_service,
    search_appointments_by_range_service,
    update_appointment_status_service,
    update_appointment_status_any_service,
    apply_completion_side_effects_service,
    reschedule_appointment_with_slots_service,
    reschedule_appointment_any_with_slots_service,
    donor_has_active_appointment_service,
    get_active_appointment_by_dni_service,
)
from app.api.v1.services.available_slots_service import (
    release_slot_service,
    list_available_days_for_request_service,
    list_available_time_ranges_for_request_service,
    list_available_slots_for_request_service,
)
from app.api.v1.services.hospital_request_service import (
    get_hospital_request_by_id_service,
    get_hospital_request_any_service,
)
from app.api.v1.services.donor_service import (
    get_donor_by_id_service,
    get_donor_by_dni_service,
)
from app.api.v1.services.donor_eligibility_service import evaluate_donor_eligibility_service
from app.api.v1.services.stock_service import crear_unidad_service
from app.schemas.stock_schema import UnidadCreate
from app.utils.auth_utils import resolve_hospital_id

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
MIN_TIME = time(7, 0)
MAX_TIME = time(20, 0)
MAX_RANGE_DAYS = 366


def _require_auth(current_user: dict):
    uid = current_user.get("uid") if current_user else None
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )


def _is_internal_auth(current_user: dict) -> bool:
    if not current_user:
        return False

    auth_type = (current_user.get("auth_type") or "").strip().upper()
    if auth_type == "INTERNAL":
        return True

    role = (current_user.get("role") or "").strip().upper()
    if role == "INTERNAL":
        return True

    uid = (current_user.get("uid") or "").strip().lower()
    return uid in {"internal", "internal_service", "vito_internal"}


def _get_donor_or_404(donor_id: str):
    donor = get_donor_by_id_service(donor_id)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return donor


def _validate_donor_is_enabled(donor: dict):
    if not donor.get("is_enabled", True):
        raise HTTPException(status_code=409, detail="Donor is disabled")


def _validate_donor_is_apt(donor_id: str):
    donor = _get_donor_or_404(donor_id)
    _validate_donor_is_enabled(donor)

    evaluation = evaluate_donor_eligibility_service(donor_id)
    if not evaluation or evaluation.get("status") != "APT":
        raise HTTPException(status_code=409, detail="Donor is not eligible to book an appointment")

    return donor


def _validate_donor_can_book(donor_id: str):
    donor = _validate_donor_is_apt(donor_id)

    donor_dni = (donor.get("dni") or "").strip()
    if donor_has_active_appointment_service(donor_id, donor_dni):
        raise HTTPException(status_code=409, detail="Donor already has an active appointment")

    return donor


def get_appointments_controller(current_user: dict):
    hospital_id = resolve_hospital_id(current_user)
    return get_appointments_service(hospital_id)


def get_appointment_by_id_controller(appointment_id: str, current_user: dict):
    hospital_id = resolve_hospital_id(current_user)

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


def get_active_appointment_by_dni_controller(dni: str, current_user: dict):
    _require_auth(current_user)

    normalized = (dni or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="dni is required")

    donor = get_donor_by_dni_service(normalized)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    appointment = get_active_appointment_by_dni_service(normalized)
    if not appointment:
        raise HTTPException(status_code=404, detail="Active appointment not found")

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


def create_appointment_from_vito_controller(body: AppointmentCreateFromVito, current_user: dict):
    _require_auth(current_user)

    req_id = body.hospital_request_id.strip()
    if not req_id:
        raise HTTPException(status_code=400, detail="hospital_request_id is required")

    hospital_request = get_hospital_request_any_service(req_id)
    if not hospital_request:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    if hospital_request.get("status") != "ACTIVO":
        raise HTTPException(status_code=409, detail="Cannot create appointment: HospitalRequest is not ACTIVO")

    try:
        end_dt = datetime.fromisoformat(hospital_request.get("end_date"))
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=BA_TZ)
    except Exception:
        raise HTTPException(status_code=409, detail="HospitalRequest has invalid end_date")

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
    appt_dt_ba = datetime.combine(body.date_local, t).replace(tzinfo=BA_TZ)

    if appt_dt_ba < now_ba:
        raise HTTPException(status_code=400, detail="Appointment datetime cannot be in the past")

    if appt_dt_ba > end_dt:
        raise HTTPException(status_code=400, detail="Appointment datetime cannot be after request end_date")

    donor = _validate_donor_can_book(body.donor_id)

    component = (hospital_request.get("component") or "").strip().upper()
    if component not in {"SANGRE", "PLAQUETAS", "MEDULA_OSEA"}:
        raise HTTPException(status_code=409, detail="HospitalRequest has invalid component")

    hospital_id = hospital_request.get("hospital_id")
    return create_appointment_from_vito_service(hospital_id, body, donor, component)


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
    _require_auth(current_user)

    if not appointment_id or not appointment_id.strip():
        raise HTTPException(status_code=400, detail="appointment_id is required")

    if _is_internal_auth(current_user):
        existing = get_appointment_any_by_id_service(appointment_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Appointment not found")

        current_status = existing.get("status")
        new_status = body.status

        if current_status == new_status:
            return existing

        if not current_status:
            raise HTTPException(status_code=409, detail="Appointment has no status")

        _validate_status_transition(current_status, new_status)

        updated = update_appointment_status_any_service(appointment_id, new_status)
        if not updated:
            raise HTTPException(status_code=404, detail="Appointment not found")

        if new_status == "CANCELADO" and current_status in {"PROGRAMADO", "CONFIRMADO"}:
            date_str = existing.get("date_local")
            time_str = existing.get("time_local")
            hospital_id = existing.get("hospital_id")
            if date_str and time_str and hospital_id:
                old_date = datetime.fromisoformat(date_str).date()
                release_slot_service(hospital_id, old_date, time_str)

        if new_status == "COMPLETADO" and current_status != "COMPLETADO":
            hospital_id = updated.get("hospital_id")
            if hospital_id:
                apply_completion_side_effects_service(hospital_id, updated)

        return updated

    hospital_id = resolve_hospital_id(current_user)

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
    _require_auth(current_user)

    if not appointment_id or not appointment_id.strip():
        raise HTTPException(status_code=400, detail="appointment_id is required")

    if _is_internal_auth(current_user):
        existing = get_appointment_any_by_id_service(appointment_id)
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

        updated = reschedule_appointment_any_with_slots_service(appointment_id, body)
        if not updated:
            raise HTTPException(status_code=404, detail="Appointment not found")

        return updated

    hospital_id = resolve_hospital_id(current_user)

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


def get_available_days_for_request_controller(
    request_id: str,
    donor_id: str,
    days_ahead: int,
    allow_existing_active: bool,
    current_user: dict,
):
    _require_auth(current_user)

    if not request_id or not request_id.strip():
        raise HTTPException(status_code=400, detail="request_id is required")

    if not donor_id or not donor_id.strip():
        raise HTTPException(status_code=400, detail="donor_id is required")

    if days_ahead <= 0:
        raise HTTPException(status_code=400, detail="days_ahead must be > 0")

    if allow_existing_active:
        _validate_donor_is_apt(donor_id)
    else:
        _validate_donor_can_book(donor_id)

    return list_available_days_for_request_service(
        request_id=request_id,
        days_ahead=days_ahead,
    )


def get_available_time_ranges_for_request_controller(
    request_id: str,
    donor_id: str,
    date_local: date,
    allow_existing_active: bool,
    current_user: dict,
):
    _require_auth(current_user)

    if not request_id or not request_id.strip():
        raise HTTPException(status_code=400, detail="request_id is required")

    if not donor_id or not donor_id.strip():
        raise HTTPException(status_code=400, detail="donor_id is required")

    if allow_existing_active:
        _validate_donor_is_apt(donor_id)
    else:
        _validate_donor_can_book(donor_id)

    return list_available_time_ranges_for_request_service(
        request_id=request_id,
        date_local=date_local,
    )


def get_available_slots_for_request_controller(
    request_id: str,
    donor_id: str,
    date_local: date,
    time_range: str | None,
    limit: int,
    offset: int,
    allow_existing_active: bool,
    current_user: dict,
):
    _require_auth(current_user)

    if not request_id or not request_id.strip():
        raise HTTPException(status_code=400, detail="request_id is required")

    if not donor_id or not donor_id.strip():
        raise HTTPException(status_code=400, detail="donor_id is required")

    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be > 0")

    if offset < 0:
        raise HTTPException(status_code=400, detail="offset must be >= 0")

    if allow_existing_active:
        _validate_donor_is_apt(donor_id)
    else:
        _validate_donor_can_book(donor_id)

    return list_available_slots_for_request_service(
        request_id=request_id,
        date_local=date_local,
        time_range=time_range,
        limit=limit,
        offset=offset,
    )


def confirmar_asistencia_controller(
    appointment_id: str,
    body: ConfirmarAsistenciaRequest,
    current_user: dict,
) -> ConfirmarAsistenciaOut:
    """
    Acción unificada de "Marcar asistencia":
    1. Cambia el turno a COMPLETADO (desde PROGRAMADO o CONFIRMADO).
    2. Crea una unidad de componente por cada ítem en body.componentes.
    3. Dispara los side-effects de completado (actualiza collected_units del pedido).
    """
    _require_auth(current_user)
    hospital_id = resolve_hospital_id(current_user)

    if not appointment_id or not appointment_id.strip():
        raise HTTPException(status_code=400, detail="appointment_id is required")

    existing = get_appointment_by_id_service(hospital_id, appointment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Appointment not found")

    current_status = existing.get("status")
    if current_status in {"CANCELADO", "COMPLETADO", "NO_PRESENTADO"}:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede marcar asistencia: el turno está en estado {current_status}",
        )

    # Cambiar estado a COMPLETADO
    updated = update_appointment_status_service(hospital_id, appointment_id, "COMPLETADO")
    if not updated:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Side-effects: actualizar collected_units en el pedido hospitalario
    apply_completion_side_effects_service(hospital_id, updated)

    # Crear una unidad por cada componente seleccionado
    donante_id = existing.get("donor_id")  # presente en turnos Vito, None en manuales
    unidades_creadas = []

    for componente in body.componentes:
        unidad = crear_unidad_service(
            componente,
            hospital_id,
            UnidadCreate(
                blood_group=body.blood_group,
                turno_id=appointment_id,
                donante_id=donante_id,
            ),
        )
        unidades_creadas.append(UnidadResumen(
            id=unidad.id,
            componente=componente,
            blood_group=unidad.blood_group,
            fecha_vencimiento=unidad.fecha_vencimiento.isoformat(),
            estado=unidad.estado,
        ))

    return ConfirmarAsistenciaOut(
        appointment_id=appointment_id,
        status="COMPLETADO",
        unidades_creadas=unidades_creadas,
    )