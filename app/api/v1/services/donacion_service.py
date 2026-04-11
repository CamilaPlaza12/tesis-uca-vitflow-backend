from typing import List

from app.schemas.stock_schema import (
    ConfirmarDonacionRequest,
    ConfirmarDonacionOut,
    UnidadCreate,
    UnidadOut,
)
from app.api.v1.services.stock_service import crear_unidad_service


def confirmar_donacion_service(hospital_id: str, body: ConfirmarDonacionRequest) -> ConfirmarDonacionOut:
    """
    Por cada componente seleccionado, crea una unidad nueva en su colección
    con estado 'disponible'. No modifica el estado del turno.
    hospital_id viene del token autenticado, no del body del request.
    """
    unidades_creadas: List[UnidadOut] = []

    for componente in body.componentes:
        unidad = crear_unidad_service(
            componente,
            hospital_id,
            UnidadCreate(
                blood_group=body.blood_group,
                turno_id=body.turno_id,
                donante_id=body.donante_id,
            ),
        )
        unidades_creadas.append(unidad)

    return ConfirmarDonacionOut(
        turno_id=body.turno_id,
        donante_id=body.donante_id,
        unidades_creadas=unidades_creadas,
    )
