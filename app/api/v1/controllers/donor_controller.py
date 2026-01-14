from fastapi import HTTPException, status
from app.schemas.donor_schema import DonorCreate, DonorUpdate
from app.api.v1.services.donor_service import (
    get_donor_by_id_service,
    get_donor_by_dni_service,
    get_all_donors_service,
    get_donors_by_blood_group_service,
    create_donor_service,
    update_donor_service,
)

def _require_auth(current_user: dict):
    uid = current_user.get("uid") if current_user else None
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

def create_donor_controller(body: DonorCreate, current_user: dict):
    _require_auth(current_user)

    res = create_donor_service(body)

    if res.get("_error") == "DNI_ALREADY_EXISTS":
        raise HTTPException(status_code=409, detail="Donor with this DNI already exists")

    if res.get("_error") == "GEOCODE_FAILED":
        raise HTTPException(status_code=422, detail="Could not geocode address_text")

    return res

def get_donor_by_id_controller(donor_id: str, current_user: dict):
    _require_auth(current_user)

    donor = get_donor_by_id_service(donor_id)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return donor

def get_donor_by_dni_controller(dni: str, current_user: dict):
    _require_auth(current_user)

    normalized = dni.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="dni is required")

    donor = get_donor_by_dni_service(normalized)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return donor

def get_all_donors_controller(current_user: dict):
    _require_auth(current_user)
    return get_all_donors_service()

def get_donors_by_blood_group_controller(blood_group: str, current_user: dict):
    _require_auth(current_user)

    valid_groups = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
    if blood_group not in valid_groups:
        raise HTTPException(status_code=400, detail="Invalid blood group")

    return get_donors_by_blood_group_service(blood_group)

def update_donor_controller(donor_id: str, body: DonorUpdate, current_user: dict):
    _require_auth(current_user)

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = update_donor_service(donor_id, patch)

    if updated is None:
        raise HTTPException(status_code=404, detail="Donor not found")

    if isinstance(updated, dict) and updated.get("_error") == "GEOCODE_FAILED":
        raise HTTPException(status_code=422, detail="Could not geocode address_text")

    return updated
