from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from app.core.internal_auth import check_internal_token
from app.firebase.firebase_client import db
from app.core.config import SUPERADMIN_UID

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    x_internal_token: str | None = Header(default=None),
    x_hospital_id: str | None = Header(default=None),
):
    # Auth interna (Vito)
    if x_internal_token is not None:
        check_internal_token(x_internal_token)
        return {
            "uid": "INTERNAL_SERVICE",
            "role": "HOSPITAL_ADMIN",
            "status": "ACTIVE",
            "hospitalId": (x_hospital_id or "").strip() or None,
        }

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta encabezado Authorization",
        )

    token = credentials.credentials

    try:
        decoded_token = firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido: falta uid",
        )

    user_ref = db.collection("users").document(uid)
    user_snap = user_ref.get()

    if not user_snap.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_data = user_snap.to_dict() or {}
    user_status = user_data.get("status") or "ACTIVE"

    # Auto-activar si era invitado y logró loguearse
    if user_status == "INVITED":
        user_ref.update({"status": "ACTIVE"})
        user_status = "ACTIVE"
        user_data["status"] = "ACTIVE"

    # Bloquear si está suspendido
    if user_status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario suspendido",
        )

    return {
        "uid": uid,
        "email": decoded_token.get("email"),
        "role": user_data.get("role"),
        "status": user_status,
        "hospitalId": user_data.get("hospitalId") or user_data.get("hospital_id"),
        "firstName": user_data.get("firstName"),
        "lastName": user_data.get("lastName"),
    }


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "HOSPITAL_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo ADMIN puede realizar esta acción",
        )
    return current_user


def require_superadmin(current_user: dict = Depends(get_current_user)):
    if not SUPERADMIN_UID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SUPERADMIN_UID no configurado en el servidor",
        )
    if current_user.get("uid") != SUPERADMIN_UID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requiere superadmin",
        )
    return current_user


def require_hospital_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "HOSPITAL_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador del hospital puede realizar esta acción",
        )
    return current_user
