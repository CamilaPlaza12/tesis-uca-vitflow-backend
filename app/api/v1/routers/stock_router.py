from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.schemas.stock_schema import (
    AgregarRequest,
    DashboardResumenOut,
    HistorialOut,
    InicializarUmbralesOut,
    RetirarBulkRequest,
    RetirarRequest,
    ResumenOut,
    TotalesOut,
    UmbralCreate,
    UmbralOut,
    UmbralPatch,
    UnidadCreate,
    UnidadOut,
    UnidadPatch,
)
from app.api.v1.controllers.stock_controller import (
    actualizar_umbral_controller,
    actualizar_unidad_controller,
    agregar_bulk_controller,
    crear_o_actualizar_umbral_controller,
    crear_unidad_controller,
    dashboard_resumen_controller,
    eliminar_unidad_controller,
    inicializar_umbrales_controller,
    listar_disponibles_controller,
    listar_historial_controller,
    listar_umbrales_controller,
    listar_unidades_controller,
    obtener_unidad_controller,
    resumen_controller,
    retirar_bulk_controller,
    retirar_unidad_controller,
    totales_disponibles_controller,
    vencer_unidad_controller,
)

router = APIRouter(prefix="/stock", tags=["Stock"])

# ─── Rutas fijas globales (deben ir ANTES de /{componente}) ──────────────────

@router.get("/totales", response_model=TotalesOut)
def totales_disponibles_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """Unidades disponibles totales del hospital autenticado, separadas por componente."""
    return totales_disponibles_controller(current_user)


@router.get("/dashboard/resumen", response_model=DashboardResumenOut)
def dashboard_resumen_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """El hospital_id se obtiene del token autenticado."""
    return dashboard_resumen_controller(current_user)


# ─── Endpoints de umbrales ────────────────────────────────────────────────────
# Definidos ANTES de /{componente} para evitar que "umbrales" sea capturado
# como valor de {componente} por FastAPI al hacer routing.

@router.get("/umbrales", response_model=List[UmbralOut])
def listar_umbrales_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """El hospital_id se obtiene del token autenticado."""
    return listar_umbrales_controller(current_user)


@router.post("/umbrales", response_model=UmbralOut, status_code=201)
def crear_o_actualizar_umbral_endpoint(
    body: UmbralCreate,
    current_user: dict = Depends(get_current_user),
):
    """El hospital_id se obtiene del token autenticado, no viene en el body."""
    return crear_o_actualizar_umbral_controller(body, current_user)


@router.patch("/umbrales/{umbral_id}", response_model=UmbralOut)
def actualizar_umbral_endpoint(
    umbral_id: str,
    body: UmbralPatch,
    current_user: dict = Depends(get_current_user),
):
    return actualizar_umbral_controller(umbral_id, body, current_user)


@router.post("/umbrales/inicializar", response_model=InicializarUmbralesOut, status_code=201)
def inicializar_umbrales_endpoint(
    current_user: dict = Depends(get_current_user),
):
    """
    Inicializa los 24 umbrales por defecto para el hospital del usuario autenticado.
    Solo crea los que no existen; no modifica los que ya tienen valor.
    El hospital_id se obtiene del token, no requiere body.
    """
    return inicializar_umbrales_controller(current_user)


# ─── Historial de movimientos ────────────────────────────────────────────────
# Debe ir ANTES de /{componente} para que "historial" no sea capturado como componente.

@router.get("/historial", response_model=List[HistorialOut])
def listar_historial_endpoint(
    componente: Optional[str] = Query(default=None),
    accion: Optional[str] = Query(default=None),
    desde: Optional[str] = Query(default=None, description="Fecha ISO (ej: 2026-04-01)"),
    hasta: Optional[str] = Query(default=None, description="Fecha ISO (ej: 2026-04-30)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Lista el historial de movimientos de stock del hospital autenticado.
    Ordenado por fecha descendente. Filtros opcionales: componente, accion, desde, hasta.
    """
    return listar_historial_controller(current_user, componente, accion, desde, hasta)


# ─── Endpoints CRUD genéricos + semánticos por componente ────────────────────

@router.post("/{componente}", response_model=UnidadOut, status_code=201)
def crear_unidad_endpoint(
    componente: str,
    body: UnidadCreate,
    current_user: dict = Depends(get_current_user),
):
    return crear_unidad_controller(componente, body, current_user)


@router.post("/{componente}/agregar", response_model=List[UnidadOut], status_code=201)
def agregar_unidad_endpoint(
    componente: str,
    body: AgregarRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Registra una o más unidades nuevas con estado 'disponible'. El hospital_id viene del token.
    El campo 'cantidad' (default 1) indica cuántas unidades crear en una sola operación.
    Registra automáticamente un movimiento en el historial de stock.
    """
    return agregar_bulk_controller(componente, body, current_user)


# Las rutas /{componente}/{sub} con sub fijo deben ir ANTES de /{componente}/{unidad_id}
@router.get("/{componente}/resumen", response_model=ResumenOut)
def resumen_endpoint(
    componente: str,
    current_user: dict = Depends(get_current_user),
):
    return resumen_controller(componente, current_user)


@router.get("/{componente}/disponibles", response_model=List[UnidadOut])
def listar_disponibles_endpoint(
    componente: str,
    blood_group: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """Lista unidades disponibles del hospital autenticado. Filtro opcional: blood_group."""
    return listar_disponibles_controller(componente, blood_group, current_user)


@router.get("/{componente}", response_model=List[UnidadOut])
def listar_unidades_endpoint(
    componente: str,
    blood_group: Optional[str] = Query(default=None),
    estado: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    """Lista unidades del hospital autenticado. Filtros opcionales: blood_group, estado."""
    return listar_unidades_controller(componente, blood_group, estado, current_user)


# ─── Retiro bulk (debe ir ANTES de /{componente}/{unidad_id}) ────────────────

@router.patch("/{componente}/retirar", response_model=List[UnidadOut])
def retirar_bulk_endpoint(
    componente: str,
    body: RetirarBulkRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Retira múltiples unidades en una sola operación. Todas pasan a estado 'usado'.
    Registra automáticamente un movimiento en el historial de stock.
    Body: { unidad_ids: [...], motivo, motivo_detalle }
    """
    return retirar_bulk_controller(componente, body, current_user)


# /{componente}/{unidad_id}/accion deben ir ANTES de /{componente}/{unidad_id}
@router.patch("/{componente}/{unidad_id}/retirar", response_model=UnidadOut)
def retirar_unidad_endpoint(
    componente: str,
    unidad_id: str,
    body: Optional[RetirarRequest] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    Marca la unidad como 'usado'. Verifica que pertenezca al hospital autenticado.
    Body opcional: { motivo, motivo_detalle }.
    motivo_detalle es obligatorio si motivo == 'otro'.
    """
    return retirar_unidad_controller(componente, unidad_id, current_user, body)


@router.patch("/{componente}/{unidad_id}/vencer", response_model=UnidadOut)
def vencer_unidad_endpoint(
    componente: str,
    unidad_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Marca la unidad como 'vencido'. Verifica que pertenezca al hospital autenticado."""
    return vencer_unidad_controller(componente, unidad_id, current_user)


@router.get("/{componente}/{unidad_id}", response_model=UnidadOut)
def obtener_unidad_endpoint(
    componente: str,
    unidad_id: str,
    current_user: dict = Depends(get_current_user),
):
    return obtener_unidad_controller(componente, unidad_id, current_user)


@router.patch("/{componente}/{unidad_id}", response_model=UnidadOut)
def actualizar_unidad_endpoint(
    componente: str,
    unidad_id: str,
    body: UnidadPatch,
    current_user: dict = Depends(get_current_user),
):
    return actualizar_unidad_controller(componente, unidad_id, body, current_user)


@router.delete("/{componente}/{unidad_id}", status_code=204)
def eliminar_unidad_endpoint(
    componente: str,
    unidad_id: str,
    current_user: dict = Depends(get_current_user),
):
    eliminar_unidad_controller(componente, unidad_id, current_user)
