from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.donor_schema import DonorCreate, DonorUpdate
from app.api.v1.controllers.donor_controller import (
    create_donor_controller,
    get_donor_by_id_controller,
    get_donor_by_dni_controller,
    update_donor_controller,
    get_all_donors_controller,
    get_donors_by_blood_group_controller,
)

router = APIRouter(prefix="/donors", tags=["Donors"])

@router.post("/")
async def create_donor_endpoint(
    body: DonorCreate,
    current_user: dict = Depends(get_current_user),
):
    return create_donor_controller(body, current_user)

@router.get("/by-dni/{dni}")
async def get_donor_by_dni_endpoint(
    dni: str,
    current_user: dict = Depends(get_current_user),
):
    return get_donor_by_dni_controller(dni, current_user)

@router.get("/")
async def get_all_donors_endpoint(
    current_user: dict = Depends(get_current_user),
):
    return get_all_donors_controller(current_user)


@router.get("/{donor_id}")
async def get_donor_by_id_endpoint(
    donor_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_donor_by_id_controller(donor_id, current_user)

@router.patch("/{donor_id}")
async def update_donor_endpoint(
    donor_id: str,
    body: DonorUpdate,
    current_user: dict = Depends(get_current_user),
):
    return update_donor_controller(donor_id, body, current_user)


@router.get("/by-blood-group/{blood_group}")
async def get_donors_by_blood_group_endpoint(
    blood_group: str,
    current_user: dict = Depends(get_current_user),
):
    return get_donors_by_blood_group_controller(blood_group, current_user)
