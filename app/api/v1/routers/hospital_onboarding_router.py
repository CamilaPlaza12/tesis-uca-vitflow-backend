from fastapi import APIRouter, Depends
from app.schemas.hospital_onboarding_schema import (
    HospitalOnboardingRequestCreate,
    HospitalOnboardingRequestReview
)
from app.api.v1.controllers.hospital_onboarding_controller import (
    create_hospital_onboarding_request_controller,
    review_hospital_onboarding_request_controller,
    get_hospital_onboarding_requests_controller
)
from app.core.security import require_superadmin

router = APIRouter(
    prefix="/hospital-onboarding",
    tags=["Hospital Onboarding"],
)

# Crear solicitud (registro hospital) — acceso público, sin autenticación
@router.post("/")
async def create_hospital_onboarding_request_endpoint(
    body: HospitalOnboardingRequestCreate,
):
    return create_hospital_onboarding_request_controller(body)

# Aprobar / Rechazar solicitud — SOLO SUPERADMIN
@router.patch("/{request_id}")
async def review_hospital_onboarding_request_endpoint(
    request_id: str,
    body: HospitalOnboardingRequestReview,
    _current_user: dict = Depends(require_superadmin),
):
    return review_hospital_onboarding_request_controller(request_id, body)

# Listar solicitudes — SOLO SUPERADMIN
@router.get("/")
async def get_hospital_onboarding_requests_endpoint(
    _current_user: dict = Depends(require_superadmin),
):
    return get_hospital_onboarding_requests_controller()
