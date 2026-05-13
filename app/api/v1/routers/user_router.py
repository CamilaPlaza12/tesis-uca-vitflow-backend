from fastapi import APIRouter, Depends

from app.core.security import require_admin, get_current_user
from app.api.v1.controllers.user_controller import (
    get_user_by_id_controller,
    create_technician_controller,
    list_hospital_users_controller,
    resend_technician_invitation_controller,
    update_user_status_controller,
)
from app.schemas.auth_schema import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/getByID/{uid}", response_model=UserResponse)
async def get_user_by_id_endpoint(
    uid: str,
    current_user: dict = Depends(get_current_user),
):
    return await get_user_by_id_controller(uid)


@router.get("")
async def list_users_endpoint(
    current_user: dict = Depends(require_admin),
):
    return list_hospital_users_controller(current_user)


@router.post("/technicians")
async def create_technician_endpoint(
    body: dict,
    current_user: dict = Depends(require_admin),
):
    return create_technician_controller(body, current_user)


@router.post("/{uid}/resend-invitation")
async def resend_technician_invitation_endpoint(
    uid: str,
    current_user: dict = Depends(require_admin),
):
    return resend_technician_invitation_controller(uid, current_user)


@router.patch("/{uid}/status")
async def update_user_status_endpoint(
    uid: str,
    body: dict,
    current_user: dict = Depends(require_admin),
):
    return update_user_status_controller(uid, body, current_user)