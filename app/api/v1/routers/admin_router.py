from fastapi import APIRouter, Depends

from app.core.security import require_superadmin
from app.api.v1.services.hospital_request_service import finalize_all_expired_requests_service
from app.api.v1.services.appointment_service import mark_past_appointments_no_presentado_service

router = APIRouter(prefix="/admin/jobs", tags=["Admin Jobs"])


@router.post("/finalizar-pedidos-vencidos")
def run_finalize_expired_requests(
    _current_user: dict = Depends(require_superadmin),
):
    """
    Dispara manualmente el job que finaliza pedidos con end_date vencido.
    Solo accesible para el superadmin.
    """
    count = finalize_all_expired_requests_service()
    return {"updated": count, "message": f"{count} pedido(s) finalizado(s)"}


@router.post("/marcar-no-presentados")
def run_mark_no_presentados(
    _current_user: dict = Depends(require_superadmin),
):
    """
    Dispara manualmente el job que marca como NO_PRESENTADO los turnos pasados.
    Solo accesible para el superadmin.
    """
    count = mark_past_appointments_no_presentado_service()
    return {"updated": count, "message": f"{count} turno(s) marcado(s) como NO_PRESENTADO"}
