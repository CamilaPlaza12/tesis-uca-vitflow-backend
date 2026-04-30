"""
Tests para la validación de donantes en eventos (tipo EVENTO).

Casos:
  1. OK: donante con turno asignado → se registra la donación
  2. ERROR: turno sin donor_id (manual) para evento → 422 DONOR_NOT_ASSIGNED_TO_EVENT
  3. ERROR: donor_id presente pero sin turno activo en el evento → 422 DONOR_NOT_ASSIGNED_TO_EVENT
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


HOSPITAL_ID = "hospital_test"
APPOINTMENT_ID = "appt_test"
DONOR_ID = "donor_test"
REQUEST_ID = "request_evento"

CURRENT_USER = {"uid": "staff_user", "hospital_id": HOSPITAL_ID}

EVENTO_REQUEST = {
    "id": REQUEST_ID,
    "hospital_id": HOSPITAL_ID,
    "tipo": "evento",
    "status": "ACTIVO",
    "component": "SANGRE",
}

BASE_APPOINTMENT = {
    "id": APPOINTMENT_ID,
    "hospital_id": HOSPITAL_ID,
    "hospital_request_id": REQUEST_ID,
    "status": "PROGRAMADO",
    "donor": {"full_name": "Juan Perez", "dni": "12345678"},
    "donation_type": "SANGRE",
}

CONFIRMAR_BODY_CLASS = None


def _get_body():
    from app.schemas.appointment_schema import ConfirmarAsistenciaRequest
    return ConfirmarAsistenciaRequest(blood_group="O+", componentes=["globulos_rojos"])


def _run(appointment_data):
    from app.api.v1.controllers.appointment_controller import confirmar_asistencia_controller
    return confirmar_asistencia_controller(APPOINTMENT_ID, _get_body(), CURRENT_USER)


# ---------------------------------------------------------------------------
# Caso 1: OK — donante con turno asignado
# ---------------------------------------------------------------------------

def test_confirmar_asistencia_evento_donor_assigned_ok():
    appointment = {**BASE_APPOINTMENT, "donor_id": DONOR_ID}
    assigned_appt = {**appointment}

    mock_unidad = MagicMock()
    mock_unidad.id = "unit_1"
    mock_unidad.blood_group = "O+"
    mock_unidad.fecha_vencimiento = MagicMock()
    mock_unidad.fecha_vencimiento.isoformat.return_value = "2026-10-01"
    mock_unidad.estado = "DISPONIBLE"

    with (
        patch("app.api.v1.controllers.appointment_controller.resolve_hospital_id", return_value=HOSPITAL_ID),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_by_id_service", return_value=appointment),
        patch("app.api.v1.controllers.appointment_controller.get_hospital_request_any_service", return_value=EVENTO_REQUEST),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_for_donor_in_request_service", return_value=assigned_appt),
        patch("app.api.v1.controllers.appointment_controller.update_appointment_status_service", return_value={**appointment, "status": "COMPLETADO"}),
        patch("app.api.v1.controllers.appointment_controller.add_blood_units_by_group_service"),
        patch("app.api.v1.controllers.appointment_controller.crear_unidad_service", return_value=mock_unidad),
    ):
        result = _run(appointment)

    assert result.status == "COMPLETADO"
    assert result.appointment_id == APPOINTMENT_ID
    assert len(result.unidades_creadas) == 1


# ---------------------------------------------------------------------------
# Caso 2: ERROR — turno manual sin donor_id para un evento
# ---------------------------------------------------------------------------

def test_confirmar_asistencia_evento_no_donor_id_raises():
    appointment = {**BASE_APPOINTMENT}  # sin donor_id

    with (
        patch("app.api.v1.controllers.appointment_controller.resolve_hospital_id", return_value=HOSPITAL_ID),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_by_id_service", return_value=appointment),
        patch("app.api.v1.controllers.appointment_controller.get_hospital_request_any_service", return_value=EVENTO_REQUEST),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _run(appointment)

    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["error"] == "DONOR_NOT_ASSIGNED_TO_EVENT"


# ---------------------------------------------------------------------------
# Caso 3: ERROR — donor_id presente pero sin turno activo en el evento
# ---------------------------------------------------------------------------

def test_confirmar_asistencia_evento_donor_not_assigned_raises():
    appointment = {**BASE_APPOINTMENT, "donor_id": DONOR_ID}

    with (
        patch("app.api.v1.controllers.appointment_controller.resolve_hospital_id", return_value=HOSPITAL_ID),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_by_id_service", return_value=appointment),
        patch("app.api.v1.controllers.appointment_controller.get_hospital_request_any_service", return_value=EVENTO_REQUEST),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_for_donor_in_request_service", return_value=None),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _run(appointment)

    assert exc_info.value.status_code == 422
    detail = exc_info.value.detail
    assert detail["error"] == "DONOR_NOT_ASSIGNED_TO_EVENT"
