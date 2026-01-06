from fastapi import APIRouter, Depends
from app.schemas.availability_schema import AvailabilityOptions, HospitalAvailability
from app.api.v1.controllers.availability_controller import get_availability_options_controller, get_hospital_availability_controller, save_hospital_availability_controller
from app.core.security import get_current_user

router = APIRouter(prefix="/availability", tags=["availability"])

@router.get("/options", response_model=AvailabilityOptions)
def get_availability_options():
    return get_availability_options_controller()

@router.put("/", response_model=HospitalAvailability)
def put_my_availability(body: HospitalAvailability, user=Depends(get_current_user)):
    hospital_id = user["uid"]
    return save_hospital_availability_controller(hospital_id, body)

@router.get("/", response_model=HospitalAvailability)
def get_my_availability(user=Depends(get_current_user)):
    hospital_id = user["uid"]
    return get_hospital_availability_controller(hospital_id)