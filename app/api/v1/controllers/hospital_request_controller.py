from fastapi import HTTPException, status
from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.hospital_request_schema import HospitalRequestCreate
from app.api.v1.services.hospital_request_service import (
    create_hospital_request_service,
    get_hospital_requests_service,
)

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

VALID_BLOOD_GROUPS = {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"}
VALID_COMPONENTS = {"SANGRE", "PLAQUETAS", "MEDULA_OSEA"}

def _get_hospital_id_or_401(current_user: dict) -> str:
    hospital_id = current_user.get("uid") if current_user else None
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )
    return hospital_id

def create_hospital_request_controller(body: HospitalRequestCreate, current_user: dict):
    hospital_id = _get_hospital_id_or_401(current_user)

    blood_group = body.blood_group.strip().upper()
    if blood_group not in VALID_BLOOD_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid blood_group")

    component = body.component.strip().upper()
    if component not in VALID_COMPONENTS:
        raise HTTPException(status_code=400, detail="Invalid component (use SANGRE / PLAQUETAS / MEDULA_OSEA)")

    requested_by = body.requested_by.strip()
    if not requested_by:
        raise HTTPException(status_code=400, detail="requested_by is required")

    now_ba_iso = datetime.now(BA_TZ).isoformat(timespec="seconds")

    return create_hospital_request_service(
        hospital_id=hospital_id,
        body=body,
        now_ba_iso=now_ba_iso,
        normalized_blood_group=blood_group,
        normalized_component=component,
    )

def get_hospital_requests_controller(current_user: dict):
    hospital_id = _get_hospital_id_or_401(current_user)
    return get_hospital_requests_service(hospital_id)
