from fastapi import HTTPException, status


def resolve_hospital_id(current_user: dict) -> str:
    """
    Extrae el hospital_id del usuario autenticado.
    El campo hospitalId es poblado por get_current_user() en security.py
    a partir del documento users/{uid} en Firestore — nunca viene del frontend.
    No realiza lecturas adicionales a Firestore: el dato ya está en current_user.
    """
    uid = current_user.get("uid") if current_user else None
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing uid",
        )

    hospital_id = (current_user.get("hospitalId") or "").strip()

    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no hospital_id associated",
        )

    return hospital_id