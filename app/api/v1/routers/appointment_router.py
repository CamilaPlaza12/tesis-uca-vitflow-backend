from fastapi import APIRouter, Depends
from datetime import date

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
    get_available_slots_for_request_controller,
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


@router.get("/request/{request_id}/available-slots")
async def get_available_slots_for_request_endpoint(
    request_id: str,
    days_ahead: int = 14,
    current_user: dict = Depends(get_current_user),
):
    return get_available_slots_for_request_controller(request_id, days_ahead, current_user)


@router.get("/{appointment_id}")
async def get_appointment_by_id_endpoint(appointment_id: str, current_user: dict = Depends(get_current_user)):
    return get_appointment_by_id_controller(appointment_id, current_user)


@router.post("/manual")
async def create_appointment_manual_endpoint(appointment: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    return create_appointment_manual_controller(appointment, current_user)


@router.post("/vito")
async def create_appointment_from_vito_endpoint(
    appointment: AppointmentCreateFromVito,
    current_user: dict = Depends(get_current_user),
):
    return create_appointment_from_vito_controller(appointment, current_user)


@router.patch("/{appointment_id}/status")
async def update_appointment_status_endpoint(appointment_id: str, body: UpdateAppointmentStatusRequest, current_user: dict = Depends(get_current_user)):
    return update_appointment_status_controller(appointment_id, body, current_user)


@router.patch("/{appointment_id}/reschedule")
async def reschedule_appointment_endpoint(appointment_id: str, body: RescheduleAppointmentRequest, current_user: dict = Depends(get_current_user)):
    return reschedule_appointment_controller(appointment_id, body, current_user)