from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.api.v1.controllers.availability_controller import (
    get_hospital_availability_controller,
    save_hospital_availability_controller,
)
from app.utils.auth_utils import resolve_hospital_id
from app.schemas.availability_schema import HospitalAvailabilityIn, HospitalAvailabilityOut

router = APIRouter(prefix="/hospital-availability", tags=["HospitalAvailability"])


@router.get("", response_model=HospitalAvailabilityOut)
def get_hospital_availability(user=Depends(get_current_user)):
    hospital_id = resolve_hospital_id(user)
    return get_hospital_availability_controller(hospital_id)


@router.put("", response_model=HospitalAvailabilityOut)
def put_hospital_availability(
    body: HospitalAvailabilityIn,
    user=Depends(get_current_user),
):
    hospital_id = resolve_hospital_id(user)
    return save_hospital_availability_controller(hospital_id, body)