from app.schemas.availability_schema import AvailabilityOptions, HospitalAvailability
from app.api.v1.services.availability_service import get_availability_options_service, get_hospital_availability_service, save_hospital_availability_service

def get_availability_options_controller() -> AvailabilityOptions:
    return get_availability_options_service()

def save_hospital_availability_controller(hospital_id: str, body: HospitalAvailability) -> HospitalAvailability:
    return save_hospital_availability_service(hospital_id, body)

def get_hospital_availability_controller(hospital_id: str) -> HospitalAvailability:
    return get_hospital_availability_service(hospital_id)