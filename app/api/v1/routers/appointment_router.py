from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.security import get_current_user
from app.schemas.appointment_schema import AppointmentCreate, UpdateAppointmentStatusRequest, RescheduleAppointmentRequest
from app.api.v1.controllers.appointment_controller import (
    get_appointments_controller,
    get_appointment_by_id_controller,
    create_appointment_manual_controller,
    update_appointment_status_controller,
    reschedule_appointment_controller,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/")
async def get_appointments_endpoint(current_user: dict = Depends(get_current_user)):
    return get_appointments_controller(current_user)


@router.get("/{appointment_id}")
async def get_appointment_by_id_endpoint(appointment_id: str, current_user: dict = Depends(get_current_user)):
    return get_appointment_by_id_controller(appointment_id, current_user)


@router.post("/manual")
async def create_appointment_manual_endpoint(appointment: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    return create_appointment_manual_controller(appointment, current_user)

@router.patch("/{appointment_id}/status")
async def update_appointment_status_endpoint(appointment_id: str, body: UpdateAppointmentStatusRequest, current_user: dict = Depends(get_current_user)):
    return update_appointment_status_controller(appointment_id, body, current_user)


@router.patch("/{appointment_id}/reschedule")
async def reschedule_appointment_endpoint(appointment_id: str, body: RescheduleAppointmentRequest, current_user: dict = Depends(get_current_user)):
    return reschedule_appointment_controller(appointment_id, body, current_user)

