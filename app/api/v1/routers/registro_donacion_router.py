import logging

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.evento_schema import ClasificarRequest
from app.api.v1.controllers.evento_controller import clasificar_donacion_controller

logger = logging.getLogger("vitflow.registros_donacion")

router = APIRouter(prefix="/registros-donacion", tags=["RegistrosDonacion"])


@router.patch("/{registro_id}/clasificar")
def clasificar_donacion_endpoint(
    registro_id: str,
    body: ClasificarRequest,
    current_user: dict = Depends(get_current_user),
):
    result = clasificar_donacion_controller(registro_id, body, current_user)
    logger.info(
        "[EVENTO] Donación clasificada — registro_id=%s componente=%s",
        registro_id,
        body.componente_donado,
    )
    return result
