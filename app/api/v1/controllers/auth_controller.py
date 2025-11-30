from fastapi import HTTPException, status

from app.schemas.auth_schema import RegisterRequest, UserResponse
from app.api.v1.services.auth_service import (
    create_firebase_user,
    create_user_profile,
    get_user_profile,
)


async def register_user_controller(data: RegisterRequest) -> UserResponse:
    user_record = await create_firebase_user(data)
    await create_user_profile(user_record.uid, data)
    return UserResponse(
        uid=user_record.uid,
        email=user_record.email,
        full_name=user_record.display_name,
        phone_number=data.phone_number,
        address=data.address,
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
            full_name=profile.get("full_name") or decoded_token.get("name"),
            phone_number=profile.get("phone_number") or decoded_token.get("phone_number"),
            address=profile.get("address"),
        )

    return UserResponse(
        uid=uid,
        email=decoded_token.get("email"),
        full_name=decoded_token.get("name"),
        phone_number=decoded_token.get("phone_number"),
        address=None,
    )
