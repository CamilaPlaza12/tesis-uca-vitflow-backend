# app/api/v1/routers/availability_router.py
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.api.v1.controllers.availability_controller import (
    get_hospital_availability_controller,
    save_hospital_availability_controller,
)

router = APIRouter(prefix="/hospital-availability", tags=["HospitalAvailability"])

from app.schemas.availability_schema import HospitalAvailabilityIn, HospitalAvailabilityOut

@router.get("", response_model=HospitalAvailabilityOut)
def get_hospital_availability(user=Depends(get_current_user)):
    uid = user["uid"]
    return get_hospital_availability_controller(uid)

@router.put("", response_model=HospitalAvailabilityOut)
def put_hospital_availability(
    body: HospitalAvailabilityIn,   # <- CAMBIO
    user=Depends(get_current_user),
):
    uid = user["uid"]
    return save_hospital_availability_controller(uid, body)
