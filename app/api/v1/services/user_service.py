from datetime import datetime
from firebase_admin import auth
from fastapi import HTTPException, status
from app.firebase.firebase_client import db

COLLECTION = "users"

VALID_USER_STATUSES = {"INVITED", "ACTIVE", "SUSPENDED"}


def create_admin_user_from_onboarding(req: dict, hospital_id: str) -> str:
    admin = req.get("admin", {})

    email = admin.get("email")
    first_name = admin.get("firstName")
    last_name = admin.get("lastName")
    phone = admin.get("phone")
    dni = admin.get("dni")

    if not email:
        raise Exception("Admin email missing in onboarding request")

    try:
        user = auth.get_user_by_email(email)
        uid = user.uid
    except auth.UserNotFoundError:
        user = auth.create_user(email=email)
        uid = user.uid

    now = datetime.utcnow().isoformat()

    user_data = {
        "uid": uid,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "phone": phone,
        "dni": dni,
        "role": "HOSPITAL_ADMIN",
        "status": "ACTIVE",
        "hospitalId": hospital_id,
        "createdAt": now,
    }

    db.collection(COLLECTION).document(uid).set(user_data, merge=True)
    return uid


def create_technician_user_service(
    *,
    hospital_id: str,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    dni: str,
) -> dict:
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hospital_id is required",
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email is required",
        )

    try:
        user = auth.get_user_by_email(email)
        uid = user.uid
    except auth.UserNotFoundError:
        user = auth.create_user(email=email)
        uid = user.uid

    existing_snap = db.collection(COLLECTION).document(uid).get()
    if existing_snap.exists:
        existing = existing_snap.to_dict() or {}
        existing_hospital_id = (
            existing.get("hospitalId") or existing.get("hospital_id") or ""
        ).strip()

        if existing_hospital_id and existing_hospital_id != hospital_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already belongs to another hospital",
            )

    now = datetime.utcnow().isoformat()
    user_data = {
        "uid": uid,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "phone": phone,
        "dni": dni,
        "role": "TECHNICIAN",
        "status": "INVITED",
        "hospitalId": hospital_id,
        "createdAt": now,
    }

    db.collection(COLLECTION).document(uid).set(user_data, merge=True)

    reset_link = auth.generate_password_reset_link(email)

    return {
        **user_data,
        "reset_link": reset_link,
    }


def list_users_by_hospital_service(hospital_id: str) -> list[dict]:
    docs = (
        db.collection(COLLECTION)
        .where("hospitalId", "==", hospital_id)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["uid"] = doc.id
        results.append(data)

    results.sort(
        key=lambda x: (
            x.get("role", ""),
            x.get("status", ""),
            x.get("firstName", ""),
            x.get("lastName", ""),
        )
    )
    return results


def resend_technician_invitation_service(hospital_id: str, uid: str) -> dict:
    doc_ref = db.collection(COLLECTION).document(uid)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = snap.to_dict() or {}

    if (user_data.get("hospitalId") or "").strip() != hospital_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get("role") != "TECHNICIAN":
        raise HTTPException(
            status_code=400,
            detail="Invitation can only be resent to technicians",
        )

    email = (user_data.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=409, detail="User has no email")

    reset_link = auth.generate_password_reset_link(email)

    return {
        **user_data,
        "uid": uid,
        "reset_link": reset_link,
    }


def update_user_status_service(hospital_id: str, uid: str, new_status: str) -> dict:
    if new_status not in VALID_USER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    doc_ref = db.collection(COLLECTION).document(uid)
    snap = doc_ref.get()

    if not snap.exists:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = snap.to_dict() or {}

    if (user_data.get("hospitalId") or "").strip() != hospital_id:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get("role") == "HOSPITAL_ADMIN":
        raise HTTPException(
            status_code=400,
            detail="HOSPITAL_ADMIN status cannot be changed",
        )

    patch = {"status": new_status}
    doc_ref.update(patch)

    return {
        **user_data,
        "uid": uid,
        **patch,
    }