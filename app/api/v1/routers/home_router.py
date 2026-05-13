from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.api.v1.controllers.home_controller import get_home_summary_controller

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/summary")
async def get_home_summary_endpoint(current_user: dict = Depends(get_current_user)):
    return get_home_summary_controller(current_user)