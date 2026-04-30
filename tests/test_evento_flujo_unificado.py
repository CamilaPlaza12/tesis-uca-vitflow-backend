"""
Tests del flujo unificado de eventos con turnos.

Flujo: PROGRAMADO/CONFIRMADO → PENDIENTE_CLASIFICACION → COMPLETADO

Casos cubiertos:
  1. registrar_donacion → pasa turno a PENDIENTE_CLASIFICACION
  2. registrar_donacion → falla si no hay turno activo (DNI sin turno)
  3. confirmar_asistencia desde PENDIENTE_CLASIFICACION → COMPLETADO (auto blood_group)
  4. confirmar_asistencia rechaza turno ya COMPLETADO
  5. transición PROGRAMADO → PENDIENTE_CLASIFICACION válida
  6. transición PENDIENTE_CLASIFICACION → COMPLETADO válida
  7. transición COMPLETADO → PENDIENTE_CLASIFICACION inválida (terminal)
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

HOSPITAL_ID = "hospital_x"
EVENTO_ID = "evento_1"
PEDIDO_ID = "pedido_evento_1"
DONOR_DNI = "11223344"
DONOR_NAME = "Ana Torres"
APPOINTMENT_ID = "appt_1"

EVENTO_DOC = {
    "hospital_id": HOSPITAL_ID,
    "estado": "ACTIVO",
    "pedido_id": PEDIDO_ID,
    "nombre": "Evento test",
    "fecha": "2026-05-01",
}

BASE_APPOINTMENT = {
    "id": APPOINTMENT_ID,
    "hospital_id": HOSPITAL_ID,
    "hospital_request_id": PEDIDO_ID,
    "status": "PROGRAMADO",
    "donor": {"full_name": DONOR_NAME, "dni": DONOR_DNI},
    "donation_type": "SANGRE",
    "donor_id": "donor_id_1",
}

CURRENT_USER = {"uid": "staff", "hospital_id": HOSPITAL_ID}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _confirmar_body(blood_group=None, componentes=None):
    from app.schemas.appointment_schema import ConfirmarAsistenciaRequest
    return ConfirmarAsistenciaRequest(
        blood_group=blood_group,
        componentes=componentes or ["globulos_rojos"],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tests de registrar_donacion_service
# ──────────────────────────────────────────────────────────────────────────────

def test_registrar_donacion_sets_pendiente_clasificacion():
    """Al registrar llegada, el turno pasa a PENDIENTE_CLASIFICACION."""
    appointment = {**BASE_APPOINTMENT, "status": "CONFIRMADO"}

    mock_snap = MagicMock()
    mock_snap.exists = True
    mock_snap.to_dict.return_value = EVENTO_DOC

    mock_appt_snap = MagicMock()
    mock_appt_snap.exists = True
    mock_appt_snap.to_dict.return_value = appointment
    mock_appt_snap.id = APPOINTMENT_ID

    mock_appt_ref = MagicMock()

    with (
        patch("app.api.v1.services.evento_service.db") as mock_db,
    ):
        # evento get
        mock_db.collection.return_value.document.return_value.get.return_value = mock_snap
        # appointments query
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = iter([mock_appt_snap])
        # appointments update
        mock_db.collection.return_value.document.return_value.update = MagicMock()

        from app.api.v1.services.evento_service import registrar_donacion_service
        result = registrar_donacion_service(HOSPITAL_ID, EVENTO_ID, DONOR_DNI)

    assert result["status"] == "PENDIENTE_CLASIFICACION"
    assert result["turno_id"] == APPOINTMENT_ID
    assert result["donante_dni"] == DONOR_DNI


def test_registrar_donacion_sin_turno_activo_raises():
    """Si no existe turno PROGRAMADO/CONFIRMADO para el DNI, lanza 422."""
    mock_snap = MagicMock()
    mock_snap.exists = True
    mock_snap.to_dict.return_value = EVENTO_DOC

    with (
        patch("app.api.v1.services.evento_service.db") as mock_db,
    ):
        mock_db.collection.return_value.document.return_value.get.return_value = mock_snap
        # no appointments found
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = iter([])

        from app.api.v1.services.evento_service import registrar_donacion_service
        with pytest.raises(HTTPException) as exc_info:
            registrar_donacion_service(HOSPITAL_ID, EVENTO_ID, DONOR_DNI)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["error"] == "DONOR_NOT_ASSIGNED_TO_EVENT"


# ──────────────────────────────────────────────────────────────────────────────
# Tests de confirmar_asistencia_controller (clasificación)
# ──────────────────────────────────────────────────────────────────────────────

def test_confirmar_asistencia_desde_pendiente_clasificacion_ok():
    """Desde PENDIENTE_CLASIFICACION, con blood_group automático, pasa a COMPLETADO."""
    appointment = {**BASE_APPOINTMENT, "status": "PENDIENTE_CLASIFICACION"}
    donor_profile = {"id": "donor_id_1", "blood_group": "O+", "first_name": "Ana", "last_name": "Torres"}

    mock_unidad = MagicMock()
    mock_unidad.id = "u1"
    mock_unidad.blood_group = "O+"
    mock_unidad.fecha_vencimiento.isoformat.return_value = "2027-01-01"
    mock_unidad.estado = "disponible"

    with (
        patch("app.api.v1.controllers.appointment_controller.resolve_hospital_id", return_value=HOSPITAL_ID),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_by_id_service", return_value=appointment),
        patch("app.api.v1.controllers.appointment_controller.get_hospital_request_any_service", return_value={"tipo": "evento"}),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_for_donor_in_request_service", return_value=appointment),
        patch("app.api.v1.controllers.appointment_controller.get_donor_by_id_service", return_value=donor_profile),
        patch("app.api.v1.controllers.appointment_controller.update_appointment_status_service", return_value={**appointment, "status": "COMPLETADO"}),
        patch("app.api.v1.controllers.appointment_controller.add_blood_units_by_group_service"),
        patch("app.api.v1.controllers.appointment_controller.crear_unidad_service", return_value=mock_unidad),
    ):
        from app.api.v1.controllers.appointment_controller import confirmar_asistencia_controller
        result = confirmar_asistencia_controller(APPOINTMENT_ID, _confirmar_body(), CURRENT_USER)

    assert result.status == "COMPLETADO"
    assert len(result.unidades_creadas) == 1


def test_confirmar_asistencia_turno_completado_raises():
    """No se puede clasificar un turno ya COMPLETADO."""
    appointment = {**BASE_APPOINTMENT, "status": "COMPLETADO"}

    with (
        patch("app.api.v1.controllers.appointment_controller.resolve_hospital_id", return_value=HOSPITAL_ID),
        patch("app.api.v1.controllers.appointment_controller.get_appointment_by_id_service", return_value=appointment),
    ):
        from app.api.v1.controllers.appointment_controller import confirmar_asistencia_controller
        with pytest.raises(HTTPException) as exc_info:
            confirmar_asistencia_controller(APPOINTMENT_ID, _confirmar_body(blood_group="O+"), CURRENT_USER)

    assert exc_info.value.status_code == 409


# ──────────────────────────────────────────────────────────────────────────────
# Tests de transiciones de estado (_validate_status_transition)
# ──────────────────────────────────────────────────────────────────────────────

def test_transition_programado_to_pendiente_ok():
    from app.api.v1.controllers.appointment_controller import _validate_status_transition
    _validate_status_transition("PROGRAMADO", "PENDIENTE_CLASIFICACION")  # no raises


def test_transition_confirmado_to_pendiente_ok():
    from app.api.v1.controllers.appointment_controller import _validate_status_transition
    _validate_status_transition("CONFIRMADO", "PENDIENTE_CLASIFICACION")  # no raises


def test_transition_pendiente_to_completado_ok():
    from app.api.v1.controllers.appointment_controller import _validate_status_transition
    _validate_status_transition("PENDIENTE_CLASIFICACION", "COMPLETADO")  # no raises


def test_transition_completado_raises():
    from app.api.v1.controllers.appointment_controller import _validate_status_transition
    with pytest.raises(HTTPException) as exc_info:
        _validate_status_transition("COMPLETADO", "PENDIENTE_CLASIFICACION")
    assert exc_info.value.status_code == 409
