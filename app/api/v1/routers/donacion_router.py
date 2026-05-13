from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.stock_schema import ConfirmarDonacionRequest, ConfirmarDonacionOut
from app.api.v1.controllers.donacion_controller import confirmar_donacion_controller

router = APIRouter(prefix="/donaciones", tags=["Donaciones"])


@router.post("/confirmar", response_model=ConfirmarDonacionOut, status_code=201)
def confirmar_donacion_endpoint(
    body: ConfirmarDonacionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Confirma la asistencia de un donante y registra los componentes obtenidos.
    El hospital_id se obtiene del token autenticado, no viene en el body.
    Por cada componente seleccionado se crea una unidad nueva (estado: disponible).
    No modifica el estado del turno.
    """
    return confirmar_donacion_controller(body, current_user)
