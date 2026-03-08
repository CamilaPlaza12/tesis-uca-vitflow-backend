from fastapi import HTTPException
from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.hospital_request_schema import HospitalRequestCreate, UpdateHospitalRequestRequest
from app.api.v1.services.hospital_request_service import (
    create_hospital_request_service,
    get_hospital_requests_service,
    update_hospital_request_service,
    get_hospital_request_by_id_service,
)
from app.api.v1.services.appointment_service import cancel_appointments_by_request_service
from app.utils.auth_utils import resolve_hospital_id

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

VALID_BLOOD_GROUPS = {"O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"}
VALID_COMPONENTS = {"SANGRE", "PLAQUETAS", "MEDULA_OSEA"}


def create_hospital_request_controller(body: HospitalRequestCreate, current_user: dict):
    hospital_id = resolve_hospital_id(current_user)

    blood_group = body.blood_group.strip().upper()
    if blood_group not in VALID_BLOOD_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid blood_group")

    component = body.component.strip().upper()
    if component not in VALID_COMPONENTS:
        raise HTTPException(
            status_code=400,
            detail="Invalid component (use SANGRE / PLAQUETAS / MEDULA_OSEA)",
        )

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
    hospital_id = resolve_hospital_id(current_user)
    return get_hospital_requests_service(hospital_id)


def update_hospital_request_controller(
    request_id: str,
    body: UpdateHospitalRequestRequest,
    current_user: dict,
):
    hospital_id = resolve_hospital_id(current_user)

    existing = get_hospital_request_by_id_service(hospital_id, request_id)
    if not existing:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    existing_status = existing.get("status")

    if existing_status in {"COMPLETO", "CANCELADO"}:
        raise HTTPException(
            status_code=409,
            detail="HospitalRequest cannot be edited in terminal status",
        )

    patch = body.model_dump(exclude_unset=True)

    if existing_status == "FINALIZADO":
        raise HTTPException(
            status_code=409,
            detail="FINALIZADO requests cannot be edited (only automatic transition to COMPLETO)",
        )

    if patch.get("status") == "COMPLETO":
        raise HTTPException(
            status_code=400,
            detail="COMPLETO status is automatic and cannot be set manually",
        )

    is_cancelling = patch.get("status") == "CANCELADO" and existing_status != "CANCELADO"

    if "comments" in patch:
        c = (patch["comments"] or "").strip()
        patch["comments"] = c or None

    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated_req = update_hospital_request_service(hospital_id, request_id, patch)

    if is_cancelling:
        cancel_appointments_by_request_service(hospital_id, request_id)

    return updated_req


def get_hospital_request_by_id_controller(request_id: str, current_user: dict):
    hospital_id = resolve_hospital_id(current_user)

    req = get_hospital_request_by_id_service(hospital_id, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="HospitalRequest not found")

    return req