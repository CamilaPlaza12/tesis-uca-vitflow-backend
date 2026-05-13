from fastapi import HTTPException, status

from app.schemas.stock_schema import ConfirmarDonacionRequest, ConfirmarDonacionOut
from app.api.v1.services.donacion_service import confirmar_donacion_service
from app.api.v1.services.stock_service import registrar_historial_service


def _get_hospital_id(current_user: dict) -> str:
    hospital_id = (current_user or {}).get("hospitalId") or ""
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario autenticado no tiene un hospital asociado",
        )
    return hospital_id


def _get_usuario_nombre(current_user: dict) -> str:
    first = (current_user or {}).get("firstName") or ""
    last = (current_user or {}).get("lastName") or ""
    nombre = f"{first} {last}".strip()
    return nombre or "Usuario desconocido"


def confirmar_donacion_controller(body: ConfirmarDonacionRequest, current_user: dict) -> ConfirmarDonacionOut:
    hospital_id = _get_hospital_id(current_user)
    resultado = confirmar_donacion_service(hospital_id, body)

    # Registrar un movimiento de historial por cada componente generado.
    # resultado.unidades_creadas[i] corresponde a body.componentes[i] (mismo orden).
    usuario_id = current_user.get("uid", "")
    usuario_nombre = _get_usuario_nombre(current_user)
    for componente, unidad in zip(body.componentes, resultado.unidades_creadas):
        registrar_historial_service(
            hospital_id=hospital_id,
            usuario_id=usuario_id,
            usuario_nombre=usuario_nombre,
            accion="agrego",
            componente=componente,
            blood_group=body.blood_group,
            unidades_ids=[unidad.id],
            cantidad=1,
        )

    return resultado
