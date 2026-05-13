from fastapi import HTTPException, status
from app.api.v1.services.nearby_donor_service import get_nearby_donors_for_request_service
from app.utils.auth_utils import resolve_hospital_id


def get_nearby_donors_for_request_controller(
    request_id: str,
    radius_km: float,
    current_user: dict,
):
    hospital_id = resolve_hospital_id(current_user)

    if not request_id or not request_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="request_id is required",
        )

    if radius_km <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="radius_km must be > 0",
        )

    return get_nearby_donors_for_request_service(
        hospital_id=hospital_id,
        request_id=request_id,
        radius_km=radius_km,
    )