from fastapi import HTTPException, status

from app.schemas.stock_schema import ConfirmarDonacionRequest, ConfirmarDonacionOut
from app.api.v1.services.donacion_service import confirmar_donacion_service


def _get_hospital_id(current_user: dict) -> str:
    hospital_id = (current_user or {}).get("hospitalId") or ""
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario autenticado no tiene un hospital asociado",
        )
    return hospital_id


def confirmar_donacion_controller(body: ConfirmarDonacionRequest, current_user: dict) -> ConfirmarDonacionOut:
    hospital_id = _get_hospital_id(current_user)
    return confirmar_donacion_service(hospital_id, body)
