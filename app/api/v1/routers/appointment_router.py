from datetime import date

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.appointment_schema import (
    AppointmentCreate,
    AppointmentCreateFromVito,
    UpdateAppointmentStatusRequest,
    RescheduleAppointmentRequest,
)
from app.api.v1.controllers.appointment_controller import (
    get_appointments_controller,
    get_appointment_by_id_controller,
    create_appointment_manual_controller,
    create_appointment_from_vito_controller,
    get_month_window_appointments_controller,
    update_appointment_status_controller,
    reschedule_appointment_controller,
    search_appointments_by_range_controller,
    get_available_days_for_request_controller,
    get_available_time_ranges_for_request_controller,
    get_available_slots_for_request_controller,
    get_active_appointment_by_dni_controller,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/")
async def get_appointments_endpoint(current_user: dict = Depends(get_current_user)):
    return get_appointments_controller(current_user)


@router.get("/search/{desde}/{hasta}")
async def search_appointments_by_range_endpoint(
    desde: date,
    hasta: date,
    current_user: dict = Depends(get_current_user),
):
    return search_appointments_by_range_controller(desde, hasta, current_user)


@router.get("/window/months")
async def get_month_window_appointments_endpoint(current_user: dict = Depends(get_current_user)):
    return get_month_window_appointments_controller(current_user)


@router.get("/by-dni/{dni}/active")
async def get_active_appointment_by_dni_endpoint(
    dni: str,
    current_user: dict = Depends(get_current_user),
):
    return get_active_appointment_by_dni_controller(dni, current_user)


@router.get("/request/{request_id}/available-days")
async def get_available_days_for_request_endpoint(
    request_id: str,
    donor_id: str,
    days_ahead: int = 14,
    allow_existing_active: bool = False,
    current_user: dict = Depends(get_current_user),
):
    return get_available_days_for_request_controller(
        request_id=request_id,
        donor_id=donor_id,
        days_ahead=days_ahead,
        allow_existing_active=allow_existing_active,
        current_user=current_user,
    )


@router.get("/request/{request_id}/available-time-ranges")
async def get_available_time_ranges_for_request_endpoint(
    request_id: str,
    donor_id: str,
    date_local: date,
    allow_existing_active: bool = False,
    current_user: dict = Depends(get_current_user),
):
    return get_available_time_ranges_for_request_controller(
        request_id=request_id,
        donor_id=donor_id,
        date_local=date_local,
        allow_existing_active=allow_existing_active,
        current_user=current_user,
    )


@router.get("/request/{request_id}/available-slots")
async def get_available_slots_for_request_endpoint(
    request_id: str,
    donor_id: str,
    date_local: date,
    time_range: str | None = None,
    limit: int = 8,
    offset: int = 0,
    allow_existing_active: bool = False,
    current_user: dict = Depends(get_current_user),
):
    return get_available_slots_for_request_controller(
        request_id=request_id,
        donor_id=donor_id,
        date_local=date_local,
        time_range=time_range,
        limit=limit,
        offset=offset,
        allow_existing_active=allow_existing_active,
        current_user=current_user,
    )


@router.get("/{appointment_id}")
async def get_appointment_by_id_endpoint(
    appointment_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_appointment_by_id_controller(appointment_id, current_user)


@router.post("/manual")
async def create_appointment_manual_endpoint(
    appointment: AppointmentCreate,
    current_user: dict = Depends(get_current_user),
):
    return create_appointment_manual_controller(appointment, current_user)


@router.post("/vito")
async def create_appointment_from_vito_endpoint(
    appointment: AppointmentCreateFromVito,
    current_user: dict = Depends(get_current_user),
):
    return create_appointment_from_vito_controller(appointment, current_user)


@router.patch("/{appointment_id}/status")
async def update_appointment_status_endpoint(
    appointment_id: str,
    body: UpdateAppointmentStatusRequest,
    current_user: dict = Depends(get_current_user),
):
    return update_appointment_status_controller(appointment_id, body, current_user)


@router.patch("/{appointment_id}/reschedule")
async def reschedule_appointment_endpoint(
    appointment_id: str,
    body: RescheduleAppointmentRequest,
    current_user: dict = Depends(get_current_user),
):
    return reschedule_appointment_controller(appointment_id, body, current_user)