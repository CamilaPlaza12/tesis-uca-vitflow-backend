from fastapi import APIRouter
from app.schemas.hospital_onboarding_schema import (
    HospitalOnboardingRequestCreate,
    HospitalOnboardingRequestReview
)
from app.api.v1.controllers.hospital_onboarding_controller import (
    create_hospital_onboarding_request_controller,
    review_hospital_onboarding_request_controller,
    get_hospital_onboarding_requests_controller
)

router = APIRouter(
    prefix="/hospital-onboarding",
    tags=["Hospital Onboarding"],
)

# Crear solicitud (registro hospital)
@router.post("/")
async def create_hospital_onboarding_request_endpoint(
    body: HospitalOnboardingRequestCreate,
):
    return create_hospital_onboarding_request_controller(body)

# Aprobar / Rechazar solicitud (backoffice)
@router.patch("/{request_id}")
async def review_hospital_onboarding_request_endpoint(
    request_id: str,
    body: HospitalOnboardingRequestReview,
):
    return review_hospital_onboarding_request_controller(request_id, body)

@router.get("/")
async def get_hospital_onboarding_requests_endpoint():
    return get_hospital_onboarding_requests_controller()
