from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status

from app.schemas.stock_schema import (
    AgregarRequest,
    DashboardResumenOut,
    HistorialOut,
    InicializarUmbralesOut,
    RetirarBulkRequest,
    RetirarRequest,
    TotalesOut,
    UmbralCreate,
    UmbralOut,
    UmbralPatch,
    UnidadCreate,
    UnidadOut,
    UnidadPatch,
    ResumenOut,
)
from app.api.v1.services.blood_bank_service import ensure_auto_request_if_low_service
from app.api.v1.services.stock_service import (
    actualizar_umbral_service,
    actualizar_unidad_service,
    agregar_bulk_service,
    crear_o_actualizar_umbral_service,
    crear_unidad_service,
    dashboard_resumen_service,
    eliminar_unidad_service,
    inicializar_umbrales_service,
    listar_disponibles_service,
    listar_historial_service,
    listar_umbrales_service,
    listar_unidades_service,
    marcar_usado_bulk_service,
    marcar_usado_service,
    marcar_vencido_service,
    obtener_unidad_service,
    registrar_historial_service,
    resumen_service,
    totales_disponibles_service,
)


def _get_usuario_nombre(current_user: dict) -> str:
    first = (current_user or {}).get("firstName") or ""
    last = (current_user or {}).get("lastName") or ""
    nombre = f"{first} {last}".strip()
    return nombre or "Usuario desconocido"


def _get_hospital_id(current_user: dict) -> str:
    """
    Extrae el hospital_id del usuario autenticado.
    El campo hospitalId es poblado por get_current_user() en security.py
    a partir del documento users/{uid} en Firestore — nunca viene del frontend.
    """
    hospital_id = (current_user or {}).get("hospitalId") or ""
    if not hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario autenticado no tiene un hospital asociado",
        )
    return hospital_id


def _validate_componente(componente: str) -> None:
    validos = {"globulos_rojos", "plasma", "plaquetas"}
    if componente not in validos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Componente inválido: '{componente}'. Valores permitidos: {sorted(validos)}",
        )


# ─── Unidades ─────────────────────────────────────────────────────────────────

def crear_unidad_controller(componente: str, body: UnidadCreate, current_user: dict) -> UnidadOut:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    return crear_unidad_service(componente, hospital_id, body)


def agregar_bulk_controller(componente: str, body: AgregarRequest, current_user: dict) -> List[UnidadOut]:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    unidades = agregar_bulk_service(componente, hospital_id, body.blood_group, body.cantidad)
    registrar_historial_service(
        hospital_id=hospital_id,
        usuario_id=current_user["uid"],
        usuario_nombre=_get_usuario_nombre(current_user),
        accion="agrego",
        componente=componente,
        blood_group=body.blood_group,
        unidades_ids=[u.id for u in unidades],
        cantidad=len(unidades),
    )
    return unidades


def retirar_bulk_controller(
    componente: str, body: RetirarBulkRequest, current_user: dict
) -> List[UnidadOut]:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    unidades = marcar_usado_bulk_service(
        componente, body.unidad_ids, hospital_id, body.motivo, body.motivo_detalle
    )
    blood_group = unidades[0].blood_group if unidades else None
    registrar_historial_service(
        hospital_id=hospital_id,
        usuario_id=current_user["uid"],
        usuario_nombre=_get_usuario_nombre(current_user),
        accion="retiro",
        componente=componente,
        blood_group=blood_group,
        unidades_ids=[u.id for u in unidades],
        cantidad=len(unidades),
        motivo=body.motivo,
        motivo_detalle=body.motivo_detalle,
    )
    if blood_group:
        ensure_auto_request_if_low_service(hospital_id, componente, blood_group)
    return unidades


def listar_unidades_controller(
    componente: str,
    blood_group: Optional[str],
    estado: Optional[str],
    current_user: dict,
) -> List[UnidadOut]:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    return listar_unidades_service(componente, hospital_id, blood_group, estado)


def obtener_unidad_controller(componente: str, unidad_id: str, current_user: dict) -> UnidadOut:
    _validate_componente(componente)
    # Verificamos que el hospital tenga acceso solo a sus propias unidades.
    # obtener_unidad_service devuelve la unidad con su hospital_id;
    # comparamos contra el del token.
    hospital_id = _get_hospital_id(current_user)
    unidad = obtener_unidad_service(componente, unidad_id)
    if unidad.hospital_id != hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La unidad no pertenece a este hospital",
        )
    return unidad


def actualizar_unidad_controller(
    componente: str, unidad_id: str, body: UnidadPatch, current_user: dict
) -> UnidadOut:
    _validate_componente(componente)
    # La verificación de ownership queda en el service de cada acción semántica.
    # Para el PATCH genérico verificamos aquí.
    hospital_id = _get_hospital_id(current_user)
    unidad = obtener_unidad_service(componente, unidad_id)
    if unidad.hospital_id != hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La unidad no pertenece a este hospital",
        )
    return actualizar_unidad_service(componente, unidad_id, body)


def eliminar_unidad_controller(componente: str, unidad_id: str, current_user: dict) -> None:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    unidad = obtener_unidad_service(componente, unidad_id)
    if unidad.hospital_id != hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La unidad no pertenece a este hospital",
        )
    eliminar_unidad_service(componente, unidad_id)


def resumen_controller(componente: str, current_user: dict) -> ResumenOut:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    return resumen_service(componente, hospital_id)


# ─── Acciones semánticas ──────────────────────────────────────────────────────

def retirar_unidad_controller(
    componente: str,
    unidad_id: str,
    current_user: dict,
    body: Optional[RetirarRequest] = None,
) -> UnidadOut:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    unidad = marcar_usado_service(
        componente,
        unidad_id,
        hospital_id,
        motivo=body.motivo if body else None,
        motivo_detalle=body.motivo_detalle if body else None,
    )
    ensure_auto_request_if_low_service(hospital_id, componente, unidad.blood_group)
    return unidad


def vencer_unidad_controller(componente: str, unidad_id: str, current_user: dict) -> UnidadOut:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    unidad = marcar_vencido_service(componente, unidad_id, hospital_id)
    ensure_auto_request_if_low_service(hospital_id, componente, unidad.blood_group)
    return unidad


def listar_disponibles_controller(
    componente: str,
    blood_group: Optional[str],
    current_user: dict,
) -> List[UnidadOut]:
    _validate_componente(componente)
    hospital_id = _get_hospital_id(current_user)
    return listar_disponibles_service(componente, hospital_id, blood_group)


# ─── Totales disponibles ─────────────────────────────────────────────────────

def totales_disponibles_controller(current_user: dict) -> TotalesOut:
    hospital_id = _get_hospital_id(current_user)
    return totales_disponibles_service(hospital_id)


# ─── Dashboard ────────────────────────────────────────────────────────────────

def dashboard_resumen_controller(current_user: dict) -> DashboardResumenOut:
    hospital_id = _get_hospital_id(current_user)
    return dashboard_resumen_service(hospital_id)


# ─── Umbrales ─────────────────────────────────────────────────────────────────

def listar_umbrales_controller(current_user: dict) -> List[UmbralOut]:
    hospital_id = _get_hospital_id(current_user)
    return listar_umbrales_service(hospital_id)


def crear_o_actualizar_umbral_controller(body: UmbralCreate, current_user: dict) -> UmbralOut:
    hospital_id = _get_hospital_id(current_user)
    return crear_o_actualizar_umbral_service(hospital_id, body)


def actualizar_umbral_controller(umbral_id: str, body: UmbralPatch, current_user: dict) -> UmbralOut:
    hospital_id = _get_hospital_id(current_user)
    return actualizar_umbral_service(umbral_id, hospital_id, body)


def inicializar_umbrales_controller(current_user: dict) -> InicializarUmbralesOut:
    hospital_id = _get_hospital_id(current_user)
    return inicializar_umbrales_service(hospital_id)


# ─── Historial ────────────────────────────────────────────────────────────────

def listar_historial_controller(
    current_user: dict,
    componente: Optional[str],
    accion: Optional[str],
    desde: Optional[str],
    hasta: Optional[str],
) -> List[HistorialOut]:
    hospital_id = _get_hospital_id(current_user)

    def _parse_fecha(valor: str, campo: str) -> datetime:
        try:
            dt = datetime.fromisoformat(valor)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Formato de '{campo}' inválido: {valor}")

    desde_dt = _parse_fecha(desde, "desde") if desde else None
    hasta_dt = _parse_fecha(hasta, "hasta") if hasta else None

    return listar_historial_service(hospital_id, componente, accion, desde_dt, hasta_dt)
