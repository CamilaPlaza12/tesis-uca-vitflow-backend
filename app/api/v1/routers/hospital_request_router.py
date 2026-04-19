from fastapi import APIRouter, Depends, Header

from app.core.security import get_current_user
from app.core.internal_auth import check_internal_token
from app.schemas.hospital_request_schema import HospitalRequestCreate, UpdateHospitalRequestRequest
from app.api.v1.controllers.hospital_request_controller import (
    create_hospital_request_controller,
    get_hospital_requests_controller,
    update_hospital_request_controller,
    get_hospital_request_by_id_controller,
    get_hospital_request_status_controller,
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

@router.patch("/{request_id}")
async def update_hospital_request_endpoint(
    request_id: str,
    body: UpdateHospitalRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    return update_hospital_request_controller(request_id, body, current_user)

@router.get("/{request_id}/status")
async def get_hospital_request_status_endpoint(
    request_id: str,
    x_internal_token: str | None = Header(default=None),
):
    check_internal_token(x_internal_token)
    return get_hospital_request_status_controller(request_id)


@router.get("/{request_id}")
async def get_hospital_request_by_id_endpoint(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_hospital_request_by_id_controller(request_id, current_user)