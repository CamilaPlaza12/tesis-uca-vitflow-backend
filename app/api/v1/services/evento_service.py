"""
Servicio para Eventos de donación.

Colecciones Firestore usadas:
  - eventos          : documentos de cada evento
  - hospital_requests: al crear un evento se genera un pedido tipo "EVENTO"
  - appointments     : los turnos son la fuente de verdad del estado de cada donante
  - donors           : para obtener el nombre del donante

Flujo de estados de turno en un evento:
  PROGRAMADO / CONFIRMADO → PENDIENTE_CLASIFICACION → COMPLETADO
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.firebase.firebase_client import db
from app.schemas.evento_schema import EventoCreate, EventoUpdate

logger = logging.getLogger(__name__)

COLLECTION_EVENTOS = "eventos"
COLLECTION_PEDIDOS = "hospital_requests"
COLLECTION_DONORS = "donors"
COLLECTIONS_COMPONENTES = ("globulos_rojos", "plasma", "plaquetas")

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# Estados que indican que el donante ya llegó al evento (llegada registrada o completado)
ARRIVED_STATUSES = {"PENDIENTE_CLASIFICACION", "COMPLETADO"}
# Estados válidos para registrar llegada (el turno aún no fue procesado)
ARRIVAL_ELIGIBLE_STATUSES = {"PROGRAMADO", "CONFIRMADO"}


def _now_ba_iso() -> str:
    return datetime.now(BA_TZ).isoformat(timespec="seconds")


def _lookup_donante_nombre(dni: str) -> str | None:
    docs = (
        db.collection(COLLECTION_DONORS)
        .where("dni", "==", dni)
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        nombre = f"{first} {last}".strip()
        return nombre or None
    return None


def _find_appointment_for_arrival(pedido_id: str, donor_dni: str) -> dict | None:
    """
    Devuelve el turno en estado PROGRAMADO o CONFIRMADO para ese DNI en ese pedido.
    Usa el campo anidado donor.dni que Firestore soporta con dot-notation.
    """
    docs = (
        db.collection("appointments")
        .where("hospital_request_id", "==", pedido_id)
        .where("donor.dni", "==", donor_dni)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        if data.get("status") in ARRIVAL_ELIGIBLE_STATUSES:
            data["id"] = doc.id
            return data
    return None


def sync_evento_cancelado_by_pedido_id(pedido_id: str) -> bool:
    """Set estado=CANCELADO on the evento linked to pedido_id. Returns True if found."""
    docs = (
        db.collection(COLLECTION_EVENTOS)
        .where("pedido_id", "==", pedido_id)
        .limit(1)
        .stream()
    )
    for doc in docs:
        db.collection(COLLECTION_EVENTOS).document(doc.id).update({
            "estado": "CANCELADO",
            "updated_at": _now_ba_iso(),
        })
        return True
    return False


def sync_evento_finalizado_by_pedido_id(pedido_id: str) -> bool:
    """Set estado=FINALIZADO on the evento linked to pedido_id. Returns True if found."""
    docs = (
        db.collection(COLLECTION_EVENTOS)
        .where("pedido_id", "==", pedido_id)
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        if data.get("estado") in {"CANCELADO", "FINALIZADO"}:
            return True
        db.collection(COLLECTION_EVENTOS).document(doc.id).update({
            "estado": "FINALIZADO",
            "updated_at": _now_ba_iso(),
        })
        return True
    return False


def create_evento_service(hospital_id: str, body: EventoCreate) -> dict:
    now_iso = _now_ba_iso()

    fecha_str = body.fecha.isoformat()
    hora_inicio_str = body.hora_inicio.strftime("%H:%M") if body.hora_inicio else None
    hora_fin_str = body.hora_fin.strftime("%H:%M") if body.hora_fin else None

    pedido_data = {
        "hospital_id": hospital_id,
        "datetime_local": now_iso,
        "hospital_unit": "Guardia",
        "component": "SANGRE",
        "blood_group": "MULTIPLE",
        "blood_groups": [g.upper() for g in body.grupos_sanguineos],
        "factores_rh": body.factores_rh,
        "priority": "NORMAL",
        "status": "ACTIVO",
        "requested_by": "Evento",
        "comments": f"Pedido generado automáticamente para el evento: {body.nombre}",
        "request_type": "EVENTO",
        "tipo": "evento",
        "end_date": f"{fecha_str}T23:59:59",
    }
    pedido_res = db.collection(COLLECTION_PEDIDOS).add(pedido_data)
    pedido_ref = pedido_res[1] if isinstance(pedido_res, (list, tuple)) and len(pedido_res) == 2 else pedido_res
    pedido_id = pedido_ref.id

    evento_data = {
        "nombre": body.nombre,
        "fecha": fecha_str,
        "hora_inicio": hora_inicio_str,
        "hora_fin": hora_fin_str,
        "lugar": body.lugar,
        "capacidad_esperada": body.capacidad_esperada,
        "estado": "ACTIVO",
        "pedido_id": pedido_id,
        "hospital_id": hospital_id,
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    evento_res = db.collection(COLLECTION_EVENTOS).add(evento_data)
    evento_ref = evento_res[1] if isinstance(evento_res, (list, tuple)) and len(evento_res) == 2 else evento_res

    return {"id": evento_ref.id, **evento_data}


def get_eventos_service(hospital_id: str) -> list:
    docs = (
        db.collection(COLLECTION_EVENTOS)
        .where("hospital_id", "==", hospital_id)
        .stream()
    )

    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        evento_id = doc.id
        pedido_id = (data.get("pedido_id") or "").strip()

        total_donaciones = 0
        if pedido_id:
            total_donaciones = sum(
                1 for snap in (
                    db.collection("appointments")
                    .where("hospital_request_id", "==", pedido_id)
                    .where("hospital_id", "==", hospital_id)
                    .stream()
                )
                if (snap.to_dict() or {}).get("status") in ARRIVED_STATUSES
            )

        results.append({
            "id": evento_id,
            "nombre": data.get("nombre", ""),
            "fecha": data.get("fecha", ""),
            "lugar": data.get("lugar"),
            "estado": data.get("estado", "ACTIVO"),
            "total_donaciones": total_donaciones,
        })

    results.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return results


def get_evento_activo_service(hospital_id: str) -> dict | None:
    docs = (
        db.collection(COLLECTION_EVENTOS)
        .where("hospital_id", "==", hospital_id)
        .where("estado", "==", "ACTIVO")
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data
    return None


def get_evento_by_id_service(hospital_id: str, evento_id: str) -> dict | None:
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        return None
    data["id"] = snap.id
    return data


def update_evento_service(hospital_id: str, evento_id: str, patch: dict) -> dict:
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if data.get("estado") != "ACTIVO":
        raise HTTPException(status_code=409, detail="Solo se pueden editar eventos ACTIVOS")

    patch["updated_at"] = _now_ba_iso()
    db.collection(COLLECTION_EVENTOS).document(evento_id).update(patch)

    updated = {**data, **patch}
    updated["id"] = evento_id
    return updated


def finalizar_evento_service(hospital_id: str, evento_id: str) -> dict:
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    estado_actual = data.get("estado")
    if estado_actual == "FINALIZADO":
        raise HTTPException(status_code=409, detail="El evento ya está finalizado")
    if estado_actual == "CANCELADO":
        raise HTTPException(status_code=409, detail="No se puede finalizar un evento cancelado")

    now_iso = _now_ba_iso()
    db.collection(COLLECTION_EVENTOS).document(evento_id).update({
        "estado": "FINALIZADO",
        "updated_at": now_iso,
    })

    pedido_id = data.get("pedido_id")
    if pedido_id:
        db.collection(COLLECTION_PEDIDOS).document(pedido_id).update({"status": "FINALIZADO"})

    return {
        "id": evento_id,
        "estado": "FINALIZADO",
        "mensaje": "Evento finalizado correctamente",
    }


def registrar_donacion_service(hospital_id: str, evento_id: str, dni: str) -> dict:
    """
    Registra la llegada del donante al evento: busca su turno activo y lo pasa a
    PENDIENTE_CLASIFICACION. No crea registros adicionales.
    """
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    if data.get("estado") != "ACTIVO":
        raise HTTPException(
            status_code=409,
            detail="Solo se pueden registrar donaciones en eventos ACTIVOS",
        )

    pedido_id = (data.get("pedido_id") or "").strip()
    if not pedido_id:
        raise HTTPException(status_code=409, detail="Evento sin pedido asociado")

    appointment = _find_appointment_for_arrival(pedido_id, dni)
    if not appointment:
        ts = _now_ba_iso()
        logger.warning(
            "EVENTO_ARRIVAL_BLOCKED no_active_appointment dni=%s pedido_id=%s evento_id=%s ts=%s",
            dni, pedido_id, evento_id, ts,
        )
        raise HTTPException(
            status_code=422,
            detail={
                "error": "DONOR_NOT_ASSIGNED_TO_EVENT",
                "message": "El donante no tiene un turno activo asignado para este evento",
            },
        )

    appointment_id = appointment["id"]
    donor = appointment.get("donor") or {}
    donante_nombre = donor.get("full_name") or _lookup_donante_nombre(dni)

    db.collection("appointments").document(appointment_id).update({
        "status": "PENDIENTE_CLASIFICACION",
    })

    logger.info(
        "EVENTO_ARRIVAL_REGISTERED turno_id=%s dni=%s evento_id=%s",
        appointment_id, dni, evento_id,
    )

    return {
        "turno_id": appointment_id,
        "donante_dni": donor.get("dni", dni),
        "donante_nombre": donante_nombre,
        "status": "PENDIENTE_CLASIFICACION",
        "mensaje": "Donante registrado como llegado. Pendiente clasificación.",
    }


def get_donaciones_evento_service(
    hospital_id: str,
    evento_id: str,
    solo_pendientes: bool = False,
) -> list:
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    pedido_id = (data.get("pedido_id") or "").strip()
    if not pedido_id:
        return []

    docs = (
        db.collection("appointments")
        .where("hospital_request_id", "==", pedido_id)
        .where("hospital_id", "==", hospital_id)
        .stream()
    )

    results = []
    for doc in docs:
        appt = doc.to_dict() or {}
        status = appt.get("status", "")

        if status not in ARRIVED_STATUSES:
            continue

        if solo_pendientes and status != "PENDIENTE_CLASIFICACION":
            continue

        donor = appt.get("donor") or {}
        results.append({
            "turno_id": doc.id,
            "donante_dni": donor.get("dni", ""),
            "donante_nombre": donor.get("full_name"),
            "status": status,
            "date_local": appt.get("date_local"),
            "time_local": appt.get("time_local"),
        })

    results.sort(key=lambda x: (x.get("date_local") or "", x.get("time_local") or ""))
    return results


def get_dashboard_service(hospital_id: str, evento_id: str) -> dict:
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    pedido_id = (data.get("pedido_id") or "").strip()

    total = 0
    pendientes = 0
    completados_ids: list[str] = []

    if pedido_id:
        for doc in (
            db.collection("appointments")
            .where("hospital_request_id", "==", pedido_id)
            .where("hospital_id", "==", hospital_id)
            .stream()
        ):
            status = (doc.to_dict() or {}).get("status", "")
            if status == "PENDIENTE_CLASIFICACION":
                total += 1
                pendientes += 1
            elif status == "COMPLETADO":
                total += 1
                completados_ids.append(doc.id)

    # Conteo de unidades creadas por componente para turnos COMPLETADOS del evento
    por_componente: dict[str, int] = {c: 0 for c in COLLECTIONS_COMPONENTES}
    for appt_id in completados_ids:
        for comp in COLLECTIONS_COMPONENTES:
            count = sum(
                1 for _ in (
                    db.collection(comp)
                    .where("turno_id", "==", appt_id)
                    .stream()
                )
            )
            por_componente[comp] += count

    capacidad = data.get("capacidad_esperada")
    porcentaje = round((total / capacidad) * 100, 2) if capacidad and capacidad > 0 else 0.0

    return {
        "evento_id": evento_id,
        "nombre": data.get("nombre", ""),
        "fecha": data.get("fecha", ""),
        "hora_inicio": data.get("hora_inicio"),
        "hora_fin": data.get("hora_fin"),
        "lugar": data.get("lugar"),
        "estado": data.get("estado", "ACTIVO"),
        "capacidad_esperada": capacidad,
        "total_donaciones_registradas": total,
        "pendientes_clasificacion": pendientes,
        "porcentaje_avance": porcentaje,
        "por_componente": por_componente,
    }
