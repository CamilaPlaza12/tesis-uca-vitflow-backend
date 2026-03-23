from fastapi import HTTPException, status

from app.schemas.auth_schema import UserResponse
from app.api.v1.services.auth_service import get_user_profile
from app.api.v1.services.user_service import (
    create_technician_user_service,
    list_users_by_hospital_service,
    resend_technician_invitation_service,
    update_user_status_service,
)
from app.api.v1.services.email_service import send_technician_invitation
from app.firebase.firebase_client import db


async def get_user_by_id_controller(uid: str) -> UserResponse:
    profile = await get_user_profile(uid)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        uid=profile.get("uid", uid),
        email=profile.get("email"),
        full_name=profile.get("full_name"),
        phone_number=profile.get("phone_number"),
        address=profile.get("address"),
        role=profile.get("role"),
        status=profile.get("status"),
    )


def create_technician_controller(body: dict, current_user: dict):
    hospital_id = (current_user.get("hospitalId") or "").strip()
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin user has no hospitalId associated",
        )

    email = (body.get("email") or "").strip()
    first_name = (body.get("firstName") or "").strip()
    last_name = (body.get("lastName") or "").strip()
    phone = (body.get("phone") or "").strip()
    dni = (body.get("dni") or "").strip()

    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if not first_name:
        raise HTTPException(status_code=400, detail="firstName is required")
    if not last_name:
        raise HTTPException(status_code=400, detail="lastName is required")
    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not dni:
        raise HTTPException(status_code=400, detail="dni is required")

    created = create_technician_user_service(
        hospital_id=hospital_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        dni=dni,
    )

    hospital_snap = db.collection("hospitals").document(hospital_id).get()
    hospital_name = "tu hospital"
    if hospital_snap.exists:
        hospital_data = hospital_snap.to_dict() or {}
        hospital_name = hospital_data.get("name") or hospital_name

    send_technician_invitation(
        email=created["email"],
        first_name=created["firstName"],
        hospital_name=hospital_name,
        reset_link=created["reset_link"],
    )

    return {
        "uid": created["uid"],
        "email": created["email"],
        "firstName": created["firstName"],
        "lastName": created["lastName"],
        "phone": created["phone"],
        "dni": created["dni"],
        "role": created["role"],
        "status": created["status"],
        "hospitalId": created["hospitalId"],
        "createdAt": created["createdAt"],
    }


def list_hospital_users_controller(current_user: dict):
    hospital_id = (current_user.get("hospitalId") or "").strip()
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no hospitalId associated",
        )

    return list_users_by_hospital_service(hospital_id)


def resend_technician_invitation_controller(uid: str, current_user: dict):
    hospital_id = (current_user.get("hospitalId") or "").strip()
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin user has no hospitalId associated",
        )

    resent = resend_technician_invitation_service(hospital_id, uid)

    hospital_snap = db.collection("hospitals").document(hospital_id).get()
    hospital_name = "tu hospital"
    if hospital_snap.exists:
        hospital_data = hospital_snap.to_dict() or {}
        hospital_name = hospital_data.get("name") or hospital_name

    send_technician_invitation(
        email=resent["email"],
        first_name=resent.get("firstName") or "equipo",
        hospital_name=hospital_name,
        reset_link=resent["reset_link"],
    )

    return {
        "ok": True,
        "uid": uid,
        "email": resent["email"],
        "status": resent.get("status"),
    }


def update_user_status_controller(uid: str, body: dict, current_user: dict):
    hospital_id = (current_user.get("hospitalId") or "").strip()
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin user has no hospitalId associated",
        )

    new_status = (body.get("status") or "").strip().upper()
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")

    updated = update_user_status_service(hospital_id, uid, new_status)

    return {
        "uid": updated["uid"],
        "email": updated.get("email"),
        "role": updated.get("role"),
        "status": updated.get("status"),
        "hospitalId": updated.get("hospitalId"),
    }