from fastapi import HTTPException, status
from app.schemas.auth_schema import UserResponse
from app.api.v1.controllers.auth_controller import get_user_profile  # reusamos tu función

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
    )
