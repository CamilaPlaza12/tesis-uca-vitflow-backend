from app.utils.auth_utils import resolve_hospital_id
from app.api.v1.services.home_service import get_home_summary_service


def get_home_summary_controller(current_user: dict):
    hospital_id = resolve_hospital_id(current_user)
    return get_home_summary_service(hospital_id)