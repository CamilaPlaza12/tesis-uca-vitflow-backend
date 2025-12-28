from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.api.v1.controllers.user_controller import get_user_by_id_controller
from app.schemas.auth_schema import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/getByID/{uid}", response_model=UserResponse)
async def get_user_by_id_endpoint(
    uid: str,
    current_user: dict = Depends(get_current_user),
):
    return await get_user_by_id_controller(uid)
