from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.hospital_request_schema import HospitalRequestCreate
from app.api.v1.controllers.hospital_request_controller import (
    create_hospital_request_controller,
    get_hospital_requests_controller,
)

router = APIRouter(prefix="/hospital-requests", tags=["HospitalRequests"])

@router.post("/")
async def create_hospital_request_endpoint(
    body: HospitalRequestCreate,
    current_user: dict = Depends(get_current_user),
):
    return create_hospital_request_controller(body, current_user)

@router.get("/")
async def get_hospital_requests_endpoint(
    current_user: dict = Depends(get_current_user),
):
    return get_hospital_requests_controller(current_user)
