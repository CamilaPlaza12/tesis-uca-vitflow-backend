from fastapi import HTTPException, status

from app.schemas.blood_bank_schema import (
    BloodBankAdjustRequest,
    BloodBankThresholdsUpdateRequest,
)
from app.api.v1.services.blood_bank_service import (
    get_or_create_blood_bank_service,
    add_stock_service,
    remove_stock_service,
    update_thresholds_service,
)

def _get_hospital_id(current_user: dict) -> str:
    hospital_id = current_user.get("uid") if current_user else None
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )
    return hospital_id


def get_blood_bank_controller(current_user: dict):
    hospital_id = _get_hospital_id(current_user)
    return get_or_create_blood_bank_service(hospital_id)


def add_stock_controller(body: BloodBankAdjustRequest, current_user: dict):
    hospital_id = _get_hospital_id(current_user)

    # validaciones “de controller” (por si querés cortar antes)
    if not body.blood_type:
        raise HTTPException(status_code=400, detail="blood_type is required")
    if body.amount_ml is None or body.amount_ml <= 0:
        raise HTTPException(status_code=400, detail="amount_ml must be > 0")

    return add_stock_service(hospital_id, body)


def remove_stock_controller(body: BloodBankAdjustRequest, current_user: dict):
    hospital_id = _get_hospital_id(current_user)

    if not body.blood_type:
        raise HTTPException(status_code=400, detail="blood_type is required")
    if body.amount_ml is None or body.amount_ml <= 0:
        raise HTTPException(status_code=400, detail="amount_ml must be > 0")

    return remove_stock_service(hospital_id, body)

def update_thresholds_controller(body: BloodBankThresholdsUpdateRequest, current_user: dict):
    hospital_id = _get_hospital_id(current_user)
    return update_thresholds_service(hospital_id, body)