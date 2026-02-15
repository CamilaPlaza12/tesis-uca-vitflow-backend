from fastapi import HTTPException, status
from app.schemas.hospital_onboarding_schema import (
    HospitalOnboardingRequestCreate,
    HospitalOnboardingRequestReview,
)
from app.api.v1.services.hospital_onboarding_service import (
    create_hospital_onboarding_request_service,
    review_hospital_onboarding_request_service,
    get_hospital_onboarding_requests_service,
    approve_hospital_onboarding_request_service,
    OnboardingFlowError
)

def create_hospital_onboarding_request_controller(
    body: HospitalOnboardingRequestCreate
):
    # status inicial fijo
    if body.status != "SUBMITTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status for onboarding request",
        )

    return create_hospital_onboarding_request_service(body)


def review_hospital_onboarding_request_controller(
    request_id: str,
    body: HospitalOnboardingRequestReview
):
    if not request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="request_id is required",
        )

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No review fields provided",
        )

    # 👉 CASO 1: APPROVED → flow grande
    if patch.get("status") == "APPROVED":
        try:
            return approve_hospital_onboarding_request_service(
                request_id,
                patch,
            )
        except OnboardingFlowError as e:
            if str(e) == "NOT_FOUND":
                raise HTTPException(status_code=404, detail="Onboarding request not found")
            if str(e) == "INVALID_STATUS":
                raise HTTPException(status_code=400, detail="Invalid onboarding status")
            if str(e) == "ALREADY_PROCESSED":
                raise HTTPException(status_code=409, detail="Onboarding already processed")
            raise HTTPException(
                status_code=500,
                detail="Failed to approve onboarding request",
            )

    # 👉 CASO 2: REJECTED → update simple
    res = review_hospital_onboarding_request_service(request_id, patch)

    if res is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding request not found",
        )

    return res

def get_hospital_onboarding_requests_controller():
    return get_hospital_onboarding_requests_service()
