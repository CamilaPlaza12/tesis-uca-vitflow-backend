from fastapi import HTTPException, status
import traceback

from app.schemas.donor_schema import DonorCreate, DonorUpdate, AddressValidationIn
from app.api.v1.services.donor_service import (
    get_donor_by_id_service,
    get_donor_by_dni_service,
    get_all_donors_service,
    get_donors_by_blood_group_service,
    create_donor_service,
    update_donor_service,
    validate_address_service,
)
from app.api.v1.services.donor_eligibility_service import (
    evaluate_donor_eligibility_service
)
from app.api.v1.services.donor_opportunity_service import (
    get_nearby_donation_opportunities_for_donor_service,
    get_campaigns_for_donor_service,
)
from app.api.v1.services.appointment_service import donor_has_active_appointment_service


def _require_auth(current_user: dict):
    uid = current_user.get("uid") if current_user else None
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )


def validate_address_controller(body: AddressValidationIn, current_user: dict):
    _require_auth(current_user)

    try:
        result = validate_address_service(body.address_text)
        if result is None:
            raise HTTPException(status_code=422, detail="Could not geocode address_text")
        return result
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en validate_address_controller")
        traceback.print_exc()
        raise


def create_donor_controller(body: DonorCreate, current_user: dict):
    _require_auth(current_user)

    try:
        res = create_donor_service(body)

        if res.get("_error") == "DNI_ALREADY_EXISTS":
            raise HTTPException(status_code=409, detail="Donor with this DNI already exists")

        if res.get("_error") == "GEOCODE_FAILED":
            raise HTTPException(status_code=422, detail="Could not geocode address_text")

        return res
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en create_donor_controller")
        traceback.print_exc()
        raise


def get_donor_by_id_controller(donor_id: str, current_user: dict):
    _require_auth(current_user)

    try:
        donor = get_donor_by_id_service(donor_id)
        if not donor:
            raise HTTPException(status_code=404, detail="Donor not found")
        return donor
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en get_donor_by_id_controller")
        traceback.print_exc()
        raise


def get_donor_by_dni_controller(dni: str, current_user: dict):
    _require_auth(current_user)

    try:
        normalized = dni.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="dni is required")

        donor = get_donor_by_dni_service(normalized)
        if not donor:
            raise HTTPException(status_code=404, detail="Donor not found")

        donor_id = donor.get("id")
        donor_dni = donor.get("dni")

        evaluation = None
        if donor_id:
            evaluation = evaluate_donor_eligibility_service(donor_id)

        eligibility_status = (
            evaluation.get("status")
            if isinstance(evaluation, dict) and evaluation.get("status")
            else donor.get("eligibility_status")
        )

        has_active_appointment = donor_has_active_appointment_service(donor_id, donor_dni)
        can_book = eligibility_status == "APT" and not has_active_appointment

        booking_block_reason = None
        if has_active_appointment:
            booking_block_reason = "ACTIVE_APPOINTMENT"
        elif eligibility_status != "APT":
            booking_block_reason = "NOT_APT"

        donor["has_active_appointment"] = has_active_appointment
        donor["can_book"] = can_book
        donor["booking_block_reason"] = booking_block_reason

        return donor
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en get_donor_by_dni_controller")
        traceback.print_exc()
        raise


def get_all_donors_controller(current_user: dict):
    _require_auth(current_user)

    try:
        return get_all_donors_service()
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en get_all_donors_controller")
        traceback.print_exc()
        raise


def get_donors_by_blood_group_controller(blood_group: str, current_user: dict):
    _require_auth(current_user)

    try:
        valid_groups = ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
        if blood_group not in valid_groups:
            raise HTTPException(status_code=400, detail="Invalid blood group")

        return get_donors_by_blood_group_service(blood_group)
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en get_donors_by_blood_group_controller")
        traceback.print_exc()
        raise


def update_donor_controller(donor_id: str, body: DonorUpdate, current_user: dict):
    _require_auth(current_user)

    try:
        patch = body.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(status_code=400, detail="No fields to update")

        updated = update_donor_service(donor_id, patch)

        if updated is None:
            raise HTTPException(status_code=404, detail="Donor not found")

        if isinstance(updated, dict) and updated.get("_error") == "GEOCODE_FAILED":
            raise HTTPException(status_code=422, detail="Could not geocode address_text")

        return updated
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en update_donor_controller")
        traceback.print_exc()
        raise


def evaluate_donor_eligibility_controller(donor_id: str, current_user: dict):
    _require_auth(current_user)

    try:
        result = evaluate_donor_eligibility_service(donor_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Donor not found")

        return result
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en evaluate_donor_eligibility_controller")
        traceback.print_exc()
        raise


def get_nearby_donation_opportunities_for_donor_controller(dni: str, radius_km: float, current_user: dict):
    _require_auth(current_user)

    try:
        normalized = dni.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="dni is required")

        if radius_km <= 0:
            raise HTTPException(status_code=400, detail="radius_km must be > 0")

        return get_nearby_donation_opportunities_for_donor_service(normalized, radius_km)
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en get_nearby_donation_opportunities_for_donor_controller")
        traceback.print_exc()
        raise


def get_campaigns_for_donor_controller(dni: str, current_user: dict):
    _require_auth(current_user)

    try:
        normalized = dni.strip()
        if not normalized:
            raise HTTPException(status_code=400, detail="dni is required")

        return get_campaigns_for_donor_service(normalized)
    except HTTPException:
        raise
    except Exception:
        print("[DONOR_CONTROLLER] ERROR en get_campaigns_for_donor_controller")
        traceback.print_exc()
        raise