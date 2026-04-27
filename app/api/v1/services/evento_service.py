"""
Servicio para Eventos de donación.

Colecciones Firestore:
  - eventos                  : documentos de cada evento
  - registros_donacion_evento: registros de donación individuales por evento
  - hospital_requests        : al crear un evento se genera un pedido tipo "EVENTO"
  - donors                   : se consulta por DNI para autocompletar el nombre del donante

Qué se encontró al analizar el modelo de Pedido existente:
  - El campo `request_type` ya existe ("NORMAL" | "CAMPAÑA"). Se almacena "EVENTO" como
    valor nuevo directamente en Firestore sin modificar el schema Pydantic existente.
  - El campo `blood_group` es un str único. Los pedidos EVENTO agregan campos extra
    `blood_groups: list[str]` y `factores_rh: list[str]` en el documento Firestore,
    sin tocar ningún schema, router ni endpoint existente.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.firebase.firebase_client import db
from app.schemas.evento_schema import EventoCreate, EventoUpdate

COLLECTION_EVENTOS = "eventos"
COLLECTION_REGISTROS = "registros_donacion_evento"
COLLECTION_PEDIDOS = "hospital_requests"
COLLECTION_DONORS = "donors"

BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


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


def create_evento_service(hospital_id: str, body: EventoCreate) -> dict:
    now_iso = _now_ba_iso()

    fecha_str = body.fecha.isoformat()
    hora_inicio_str = body.hora_inicio.strftime("%H:%M") if body.hora_inicio else None
    hora_fin_str = body.hora_fin.strftime("%H:%M") if body.hora_fin else None

    # Crear el hospital_request asociado al evento.
    # Campos extra blood_groups y factores_rh conviven con la estructura normal;
    # blood_group se fija en "MULTIPLE" para identificar pedidos multi-grupo.
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

        total_donaciones = sum(
            1 for _ in (
                db.collection(COLLECTION_REGISTROS)
                .where("evento_id", "==", evento_id)
                .stream()
            )
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

    existing = list(
        db.collection(COLLECTION_REGISTROS)
        .where("evento_id", "==", evento_id)
        .where("donante_dni", "==", dni)
        .limit(1)
        .stream()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Este DNI ya fue registrado en este evento")

    donante_nombre = _lookup_donante_nombre(dni)

    now_iso = _now_ba_iso()
    registro_data = {
        "evento_id": evento_id,
        "donante_dni": dni,
        "donante_nombre": donante_nombre,
        "timestamp_donacion": now_iso,
        "componente_donado": None,
    }

    res = db.collection(COLLECTION_REGISTROS).add(registro_data)
    reg_ref = res[1] if isinstance(res, (list, tuple)) and len(res) == 2 else res

    return {
        "registro_id": reg_ref.id,
        "donante_dni": dni,
        "donante_nombre": donante_nombre,
        "timestamp_donacion": now_iso,
        "mensaje": "Donación registrada correctamente",
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

    docs = (
        db.collection(COLLECTION_REGISTROS)
        .where("evento_id", "==", evento_id)
        .stream()
    )

    results = []
    for doc in docs:
        reg = doc.to_dict() or {}
        componente = reg.get("componente_donado")

        if solo_pendientes and componente is not None:
            continue

        results.append({
            "registro_id": doc.id,
            "donante_dni": reg.get("donante_dni", ""),
            "donante_nombre": reg.get("donante_nombre"),
            "timestamp_donacion": reg.get("timestamp_donacion", ""),
            "componente_donado": componente,
        })

    results.sort(key=lambda x: x.get("timestamp_donacion", ""))
    return results


def clasificar_donacion_service(
    registro_id: str,
    componente_donado: str,
    hospital_id: str,
) -> dict:
    snap = db.collection(COLLECTION_REGISTROS).document(registro_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Registro de donación no encontrado")

    reg_data = snap.to_dict() or {}

    # Verificar que el evento asociado pertenece al hospital autenticado
    evento_id = reg_data.get("evento_id", "")
    evento_snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not evento_snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    if (evento_snap.to_dict() or {}).get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Registro de donación no encontrado")

    db.collection(COLLECTION_REGISTROS).document(registro_id).update({
        "componente_donado": componente_donado,
    })

    return {
        "registro_id": registro_id,
        "donante_dni": reg_data.get("donante_dni", ""),
        "donante_nombre": reg_data.get("donante_nombre"),
        "componente_donado": componente_donado,
        "mensaje": "Clasificación guardada correctamente",
    }


def get_dashboard_service(hospital_id: str, evento_id: str) -> dict:
    snap = db.collection(COLLECTION_EVENTOS).document(evento_id).get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    data = snap.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    registros = [
        (doc.to_dict() or {})
        for doc in db.collection(COLLECTION_REGISTROS).where("evento_id", "==", evento_id).stream()
    ]

    total = len(registros)
    pendientes = sum(1 for r in registros if r.get("componente_donado") is None)

    por_componente = {
        "plasma": 0,
        "plaquetas": 0,
        "globulos_rojos": 0,
        "sangre_entera": 0,
        "sin_clasificar": 0,
    }
    for r in registros:
        comp = r.get("componente_donado")
        if comp == "PLASMA":
            por_componente["plasma"] += 1
        elif comp == "PLAQUETAS":
            por_componente["plaquetas"] += 1
        elif comp == "GLOBULOS_ROJOS":
            por_componente["globulos_rojos"] += 1
        elif comp == "SANGRE_ENTERA":
            por_componente["sangre_entera"] += 1
        else:
            por_componente["sin_clasificar"] += 1

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
