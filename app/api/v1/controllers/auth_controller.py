from fastapi import HTTPException, status

from app.schemas.auth_schema import RegisterRequest, UserResponse
from app.api.v1.services.auth_service import (
    create_firebase_user,
    create_user_profile,
    get_user_profile,
    get_me_full_service,
)


async def register_user_controller(data: RegisterRequest) -> UserResponse:
    user_record = await create_firebase_user(data)
    await create_user_profile(user_record.uid, data)

    return UserResponse(
        uid=user_record.uid,
        email=user_record.email,
        firstName=data.full_name,  # temporal para register clásico
        lastName=None,
        phone=data.phone_number,
        dni=None,
        role=None,
        status=None,
        hospitalId=None,
        createdAt=None,
    )


async def me_controller(decoded_token: dict) -> UserResponse:
    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta identificador de usuario.",
        )

    profile = await get_user_profile(uid)

    if profile:
        return UserResponse(
            uid=profile.get("uid", uid),
            email=profile.get("email") or decoded_token.get("email"),
            firstName=profile.get("firstName"),
            lastName=profile.get("lastName"),
            phone=profile.get("phone") or profile.get("phone_number"),
            dni=profile.get("dni"),
            role=profile.get("role"),
            status=profile.get("status"),
            hospitalId=profile.get("hospitalId") or profile.get("hospital_id"),
            createdAt=profile.get("createdAt"),
        )

    return UserResponse(
        uid=uid,
        email=decoded_token.get("email"),
        firstName=None,
        lastName=None,
        phone=None,
        dni=None,
        role=None,
        status=None,
        hospitalId=None,
        createdAt=None,
    )


async def me_full_controller(decoded_token: dict):
    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta identificador de usuario.",
        )

    result = await get_me_full_service(uid)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return result