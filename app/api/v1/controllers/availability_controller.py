from app.api.v1.services.availability_service import (
    get_hospital_availability_service,
    save_hospital_availability_service,
)

from app.schemas.availability_schema import HospitalAvailabilityIn, HospitalAvailabilityOut

def save_hospital_availability_controller(hospital_id: str, body: HospitalAvailabilityIn) -> HospitalAvailabilityOut:
    return save_hospital_availability_service(hospital_id, body)

def get_hospital_availability_controller(hospital_id: str) -> HospitalAvailabilityOut:
    return get_hospital_availability_service(hospital_id)
