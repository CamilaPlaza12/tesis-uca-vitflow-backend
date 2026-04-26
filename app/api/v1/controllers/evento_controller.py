from fastapi import HTTPException

from app.schemas.evento_schema import (
    EventoCreate,
    EventoUpdate,
    RegistrarDonacionRequest,
    ClasificarRequest,
)
from app.api.v1.services.evento_service import (
    create_evento_service,
    get_eventos_service,
    get_evento_activo_service,
    update_evento_service,
    finalizar_evento_service,
    registrar_donacion_service,
    get_donaciones_evento_service,
    clasificar_donacion_service,
    get_dashboard_service,
)
from app.utils.auth_utils import resolve_hospital_id

VALID_GRUPOS = {"A", "B", "AB", "O"}
VALID_FACTORES = {"+", "-"}


def create_evento_controller(body: EventoCreate, current_user: dict) -> dict:
    hospital_id = resolve_hospital_id(current_user)

    for g in body.grupos_sanguineos:
        if g.upper() not in VALID_GRUPOS:
            raise HTTPException(status_code=400, detail=f"Grupo sanguíneo inválido: {g}")

    for f in body.factores_rh:
        if f not in VALID_FACTORES:
            raise HTTPException(status_code=400, detail=f"Factor Rh inválido: {f}")

    return create_evento_service(hospital_id, body)


def get_eventos_controller(current_user: dict) -> list:
    hospital_id = resolve_hospital_id(current_user)
    return get_eventos_service(hospital_id)


def get_evento_activo_controller(current_user: dict) -> dict:
    hospital_id = resolve_hospital_id(current_user)
    evento = get_evento_activo_service(hospital_id)
    if not evento:
        raise HTTPException(status_code=404, detail="No hay ningún evento activo")
    return evento


def update_evento_controller(evento_id: str, body: EventoUpdate, current_user: dict) -> dict:
    hospital_id = resolve_hospital_id(current_user)

    raw = body.model_dump(exclude_unset=True)
    patch = {}
    for key, value in raw.items():
        if key == "fecha":
            patch["fecha"] = value.isoformat() if value is not None else None
        elif key in ("hora_inicio", "hora_fin"):
            patch[key] = value.strftime("%H:%M") if value is not None else None
        else:
            patch[key] = value

    if not patch:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    return update_evento_service(hospital_id, evento_id, patch)


def finalizar_evento_controller(evento_id: str, current_user: dict) -> dict:
    hospital_id = resolve_hospital_id(current_user)
    return finalizar_evento_service(hospital_id, evento_id)


def registrar_donacion_controller(
    evento_id: str,
    body: RegistrarDonacionRequest,
    current_user: dict,
) -> dict:
    hospital_id = resolve_hospital_id(current_user)
    dni = body.dni.strip()
    if not dni:
        raise HTTPException(status_code=400, detail="El DNI es requerido")
    return registrar_donacion_service(hospital_id, evento_id, dni)


def get_donaciones_controller(evento_id: str, current_user: dict) -> list:
    hospital_id = resolve_hospital_id(current_user)
    return get_donaciones_evento_service(hospital_id, evento_id)


def get_pendientes_clasificacion_controller(evento_id: str, current_user: dict) -> list:
    hospital_id = resolve_hospital_id(current_user)
    return get_donaciones_evento_service(hospital_id, evento_id, solo_pendientes=True)


def clasificar_donacion_controller(
    registro_id: str,
    body: ClasificarRequest,
    current_user: dict,
) -> dict:
    hospital_id = resolve_hospital_id(current_user)
    return clasificar_donacion_service(registro_id, body.componente_donado, hospital_id)


def get_dashboard_controller(evento_id: str, current_user: dict) -> dict:
    hospital_id = resolve_hospital_id(current_user)
    return get_dashboard_service(hospital_id, evento_id)
