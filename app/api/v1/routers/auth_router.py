from fastapi import APIRouter, Depends

from app.schemas.auth_schema import RegisterRequest, UserResponse
from app.api.v1.controllers.auth_controller import (
    register_user_controller,
    me_controller,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register_user_endpoint(data: RegisterRequest):
    return await register_user_controller(data)


@router.get("/me", response_model=UserResponse)
async def get_me_endpoint(current_user: dict = Depends(get_current_user)):
    return await me_controller(current_user)
