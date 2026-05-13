import logging

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.security import get_current_user
from app.schemas.evento_schema import EventoCreate, EventoUpdate, RegistrarDonacionRequest
from app.api.v1.controllers.evento_controller import (
    create_evento_controller,
    get_eventos_controller,
    get_evento_activo_controller,
    get_evento_by_id_controller,
    update_evento_controller,
    finalizar_evento_controller,
    registrar_donacion_controller,
    get_donaciones_controller,
    get_pendientes_clasificacion_controller,
    get_dashboard_controller,
)
# Clasificación de donaciones: usar POST /appointments/{appointment_id}/confirmar-asistencia
from app.api.v1.services.vito_notification_service import notify_vito_for_new_request

logger = logging.getLogger("vitflow.eventos")

router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.post("/", status_code=201)
def create_evento_endpoint(
    body: EventoCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    result = create_evento_controller(body, current_user)

    pedido_id = result.get("pedido_id")
    hospital_id = result.get("hospital_id")

    logger.info(
        "[EVENTO] Creado — id=%s hospital_id=%s nombre=%s fecha=%s pedido_id=%s",
        result.get("id"),
        hospital_id,
        result.get("nombre"),
        result.get("fecha"),
        pedido_id,
    )

    if pedido_id and hospital_id:
        logger.info(
            "[EVENTO] Agendando notificación Vito para pedido EVENTO — pedido_id=%s",
            pedido_id,
        )
        background_tasks.add_task(notify_vito_for_new_request, hospital_id, pedido_id)

    return result


# /activo debe estar antes de /{evento_id} para evitar conflictos de ruta
@router.get("/activo/")
def get_evento_activo_endpoint(
    current_user: dict = Depends(get_current_user),
):
    return get_evento_activo_controller(current_user)


@router.get("/")
def get_eventos_endpoint(
    current_user: dict = Depends(get_current_user),
):
    return get_eventos_controller(current_user)


@router.get("/{evento_id}")
def get_evento_endpoint(
    evento_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_evento_by_id_controller(evento_id, current_user)


@router.patch("/{evento_id}/finalizar")
def finalizar_evento_endpoint(
    evento_id: str,
    current_user: dict = Depends(get_current_user),
):
    result = finalizar_evento_controller(evento_id, current_user)
    logger.info("[EVENTO] Finalizado — id=%s", evento_id)
    return result


@router.patch("/{evento_id}")
def update_evento_endpoint(
    evento_id: str,
    body: EventoUpdate,
    current_user: dict = Depends(get_current_user),
):
    return update_evento_controller(evento_id, body, current_user)


@router.post("/{evento_id}/registrar-donacion", status_code=201)
def registrar_donacion_endpoint(
    evento_id: str,
    body: RegistrarDonacionRequest,
    current_user: dict = Depends(get_current_user),
):
    result = registrar_donacion_controller(evento_id, body, current_user)
    logger.info(
        "[EVENTO] Donación registrada — evento_id=%s dni=%s registro_id=%s",
        evento_id,
        body.dni,
        result.get("registro_id"),
    )
    return result


@router.get("/{evento_id}/donaciones")
def get_donaciones_endpoint(
    evento_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_donaciones_controller(evento_id, current_user)


@router.get("/{evento_id}/pendientes-clasificacion")
def get_pendientes_clasificacion_endpoint(
    evento_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_pendientes_clasificacion_controller(evento_id, current_user)


@router.get("/{evento_id}/dashboard")
def get_dashboard_endpoint(
    evento_id: str,
    current_user: dict = Depends(get_current_user),
):
    return get_dashboard_controller(evento_id, current_user)
