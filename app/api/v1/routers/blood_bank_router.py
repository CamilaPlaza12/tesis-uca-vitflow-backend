from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.blood_bank_schema import BloodBankOut, BloodBankAdjustRequest, BloodBankThresholdsUpdateRequest
from app.api.v1.controllers.blood_bank_controller import (
    get_blood_bank_controller,
    add_stock_controller,
    remove_stock_controller,
    update_thresholds_controller,
)

router = APIRouter(prefix="/blood-bank", tags=["BloodBank"])

@router.get("", response_model=BloodBankOut)
async def get_blood_bank_endpoint(current_user: dict = Depends(get_current_user)):
    return await get_blood_bank_controller(current_user)

@router.patch("/add-stock", response_model=BloodBankOut)
async def add_stock_endpoint(body: BloodBankAdjustRequest, current_user: dict = Depends(get_current_user)):
    return await add_stock_controller(body, current_user)

@router.patch("/remove-stock", response_model=BloodBankOut)
async def remove_stock_endpoint(body: BloodBankAdjustRequest, current_user: dict = Depends(get_current_user)):
    return await remove_stock_controller(body, current_user)

@router.patch("/thresholds", response_model=BloodBankOut)
async def update_thresholds_endpoint(
    body: BloodBankThresholdsUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    return await update_thresholds_controller(body, current_user)