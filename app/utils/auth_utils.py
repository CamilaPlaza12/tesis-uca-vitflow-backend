from fastapi import HTTPException, status
from app.firebase.firebase_client import db


def resolve_hospital_id(current_user: dict) -> str:
    uid = current_user.get("uid") if current_user else None
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

    user_snap = db.collection("users").document(uid).get()
    if not user_snap.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_data = user_snap.to_dict() or {}
    hospital_id = (user_data.get("hospital_id") or user_data.get("hospitalId") or "").strip()

    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no hospital_id associated",
        )

    return hospital_id