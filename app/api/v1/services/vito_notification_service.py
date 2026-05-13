import logging
import httpx

from app.core.config import VITO_NOTIFY_URL, VITO_NOTIFY_TIMEOUT
from app.api.v1.services.nearby_donor_service import get_nearby_donors_for_request_service

logger = logging.getLogger("vitflow.vito")

NEARBY_RADIUS_KM = 5.0


def notify_vito_for_new_request(hospital_id: str, request_id: str) -> None:
    """
    Background task: busca donantes cercanos para el pedido y notifica a Vito.
    Se ejecuta después de crear un hospital_request.
    """
    logger.info(
        "[VITO] Iniciando flujo post-creación — request_id=%s hospital_id=%s",
        request_id,
        hospital_id,
    )

    # 1) Buscar donantes cercanos (equivalente a GET /donors/nearby-for-request/{id})
    logger.info(
        "[VITO] Llamando a nearby-for-request — request_id=%s radius_km=%s",
        request_id,
        NEARBY_RADIUS_KM,
    )

    try:
        nearby = get_nearby_donors_for_request_service(
            hospital_id=hospital_id,
            request_id=request_id,
            radius_km=NEARBY_RADIUS_KM,
        )
    except Exception as exc:
        logger.error(
            "[VITO] Error al buscar donantes cercanos — request_id=%s error=%s",
            request_id,
            exc,
        )
        return

    total = nearby.get("total", 0)
    donors = nearby.get("donors", [])
    blood_group = nearby.get("blood_group", "")

    logger.info(
        "[VITO] Donantes compatibles encontrados — request_id=%s blood_group=%s total=%d",
        request_id,
        blood_group,
        total,
    )

    if total == 0:
        logger.info(
            "[VITO] Sin donantes compatibles, no se notifica a Vito — request_id=%s",
            request_id,
        )
        return

    for d in donors:
        logger.info(
            "[VITO]   donante id=%s nombre='%s %s' dni=%s distancia_km=%s",
            d.get("id"),
            d.get("first_name"),
            d.get("last_name"),
            d.get("dni"),
            d.get("distance_km"),
        )

    # 2) Notificar a Vito
    if not VITO_NOTIFY_URL:
        logger.warning(
            "[VITO] VITO_NOTIFY_URL no configurada — se omite la notificación (request_id=%s)",
            request_id,
        )
        return

    payload = {
        "hospital_request_id": request_id,
        "hospital_id": hospital_id,
        "blood_group": blood_group,
        "donors": donors,
    }

    logger.info(
        "[VITO] Enviando notificación a Vito — url=%s request_id=%s donors_count=%d payload=%s",
        VITO_NOTIFY_URL,
        request_id,
        total,
        payload,
    )

    try:
        response = httpx.post(
            VITO_NOTIFY_URL,
            json=payload,
            timeout=VITO_NOTIFY_TIMEOUT,
        )
        logger.info(
            "[VITO] Respuesta de Vito — request_id=%s status_code=%d body=%s",
            request_id,
            response.status_code,
            response.text[:500],
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "[VITO] Vito respondió con error HTTP — request_id=%s status_code=%d body=%s",
            request_id,
            exc.response.status_code,
            exc.response.text[:500],
        )
    except httpx.RequestError as exc:
        logger.error(
            "[VITO] Error de conexión al notificar a Vito — request_id=%s error=%s",
            request_id,
            exc,
        )


def notify_vito_for_canceled_request(
    hospital_id: str,
    request_id: str,
    donor_ids: list[str],
) -> None:
    """
    Background task: notifica a Vito que un pedido fue cancelado.
    Incluye la lista de donor_ids afectados para que Vito pueda avisar a los donantes.
    La integración HTTP con Vito aún no está implementada — por ahora solo se loguea el payload.
    """
    payload = {
        "type": "REQUEST_CANCELED",
        "request_id": request_id,
        "hospital_id": hospital_id,
        "donor_ids": donor_ids,
    }

    logger.info(
        "[VITO][CANCEL] Pedido cancelado — request_id=%s hospital_id=%s donors_afectados=%d payload=%s",
        request_id,
        hospital_id,
        len(donor_ids),
        payload,
    )

    # TODO: enviar HTTP POST a VITO_CANCEL_URL cuando el endpoint de Vito esté disponible.
    # Ejemplo:
    #   response = httpx.post(VITO_CANCEL_URL, json=payload, timeout=VITO_NOTIFY_TIMEOUT)
    #   response.raise_for_status()
