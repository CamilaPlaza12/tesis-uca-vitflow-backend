from app.firebase.firebase_client import db
from app.schemas.hospital_onboarding_schema import HospitalOnboardingRequestCreate

from firebase_admin import auth
from app.api.v1.services.email_service import (
    send_onboarding_approved,
    send_onboarding_rejected,
)

from app.api.v1.services.hospital_service import (
    create_hospital_from_onboarding_request,
)
from app.api.v1.services.user_service import (
    create_admin_user_from_onboarding,
)

from app.api.v1.services.email_service import (
    send_new_onboarding_to_vitflow,
    send_onboarding_received_to_admin,
)

from datetime import datetime

COLLECTION = "hospital_onboarding_requests"

class OnboardingFlowError(Exception):
    pass


def create_hospital_onboarding_request_service(
    body: HospitalOnboardingRequestCreate
):
    data = body.model_dump()

    res = db.collection(COLLECTION).add(data)
    doc_ref = res[1] if isinstance(res, (list, tuple)) else res

    # 🔥 Mails acá
    send_new_onboarding_to_vitflow(data)
    send_onboarding_received_to_admin(data)

    return {
        "id": doc_ref.id,
        **data
    }



def review_hospital_onboarding_request_service(
    request_id: str,
    patch: dict
):
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        return None

    existing = snap.to_dict() or {}

    doc_ref.update(patch)

    # 🔥 Si fue rechazado, mandar mail
    if patch.get("status") == "REJECTED":
        send_onboarding_rejected(existing, patch.get("reviewNote"))


    updated = {
        **existing,
        **patch,
        "id": request_id,
    }

    return updated

def get_hospital_onboarding_requests_service():
    docs = db.collection("hospital_onboarding_requests").stream()

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id

        # 🔥 SOLO DEVOLVER SUBMITTED
        if data.get("status") == "SUBMITTED":
            results.append(data)

    return results


def mark_onboarding_request_approved(
    request_id: str,
    hospital_id: str,
    admin_uid: str,
    review: dict,
):
    now = datetime.utcnow().isoformat()

    patch = {
        "status": "APPROVED",
        "processedAt": now,
        "hospitalId": hospital_id,
        "adminUid": admin_uid,
        "reviewedBy": review.get("reviewedBy"),
        "reviewedAt": review.get("reviewedAt", now),
        "reviewNote": review.get("reviewNote"),
        "updatedAt": now,
    }

    db.collection(COLLECTION).document(request_id).update(patch)
    return patch


def approve_hospital_onboarding_request_service(
    request_id: str,
    review: dict,
):
    # 1) traer request
    doc_ref = db.collection(COLLECTION).document(request_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise OnboardingFlowError("NOT_FOUND")

    req = snap.to_dict() or {}

    # 2) validaciones
    if req.get("status") != "SUBMITTED":
        raise OnboardingFlowError("INVALID_STATUS")

    if req.get("processedAt"):
        raise OnboardingFlowError("ALREADY_PROCESSED")

        # 3) crear hospital
    hospital_id = create_hospital_from_onboarding_request(
        request_id,
        req,
    )

    # 4) crear user admin
    admin_uid = create_admin_user_from_onboarding(
        req,
        hospital_id,
    )

    # 🔥 5) generar reset link
    reset_link = auth.generate_password_reset_link(req["admin"]["email"])

    # 🔥 6) mandar mail aprobación
    send_onboarding_approved(req, reset_link)

    # 7) cerrar request
    return mark_onboarding_request_approved(
        request_id=request_id,
        hospital_id=hospital_id,
        admin_uid=admin_uid,
        review=review,
    )

