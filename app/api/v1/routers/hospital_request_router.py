import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header

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
from app.api.v1.services.vito_notification_service import notify_vito_for_new_request
from app.utils.auth_utils import resolve_hospital_id

logger = logging.getLogger("vitflow.hospital_request")

router = APIRouter(prefix="/hospital-requests", tags=["HospitalRequests"])

@router.post("/")
async def create_hospital_request_endpoint(
    body: HospitalRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    result = create_hospital_request_controller(body, current_user)

    request_id = result.get("id")
    hospital_id = resolve_hospital_id(current_user)

    logger.info(
        "[PEDIDO] Pedido creado — request_id=%s hospital_id=%s blood_group=%s component=%s priority=%s",
        request_id,
        hospital_id,
        result.get("blood_group"),
        result.get("component"),
        result.get("priority"),
    )
    logger.info(
        "[PEDIDO] Agendando notificación a Vito en background — request_id=%s",
        request_id,
    )

    background_tasks.add_task(notify_vito_for_new_request, hospital_id, request_id)

    return result

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