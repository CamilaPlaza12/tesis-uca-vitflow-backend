from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status

from app.firebase.firebase_client import db
from app.schemas.stock_schema import (
    VIDA_UTIL_DIAS,
    BloodGroup,
    Componente,
    EstadoUnidad,
    HistorialOut,
    InicializarUmbralesOut,
    TotalesOut,
    UmbralCreate,
    UmbralPatch,
    UmbralOut,
    UnidadCreate,
    UnidadOut,
    UnidadPatch,
    ResumenOut,
    DashboardResumenOut,
)

# Valores por defecto de umbral mínimo por componente
UMBRALES_DEFAULT: dict = {
    "globulos_rojos": 5,
    "plasma": 3,
    "plaquetas": 2,
}

_TODOS_LOS_GRUPOS_LIST = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# TODO: Donación por aféresis
# La donación exclusiva de plaquetas por aféresis requiere
# un tipo de turno diferente al turno genérico actual.
# En esta modalidad el donante dona únicamente plaquetas,
# en mayor cantidad que en una donación de sangre completa.
# Implementar como una fase separada:
# - Nuevo tipo de turno: "aferesis"
# - Flujo de confirmación propio
# - Las unidades generadas van igualmente a la colección "plaquetas"
# - Considerar si se modela cantidad diferencial o se mantiene 1 unidad

# FIRESTORE INDEX REQUERIDO:
# Colección: globulos_rojos
# Campos: hospital_id ASC, blood_group ASC, estado ASC

# FIRESTORE INDEX REQUERIDO:
# Colección: plasma
# Campos: hospital_id ASC, blood_group ASC, estado ASC

# FIRESTORE INDEX REQUERIDO:
# Colección: plaquetas
# Campos: hospital_id ASC, blood_group ASC, estado ASC

# FIRESTORE INDEX REQUERIDO:
# Colección: stock_umbrales
# Campos: hospital_id ASC, componente ASC, blood_group ASC

COLECCION_HISTORIAL = "stock_historial"

# FIRESTORE INDEX REQUERIDO para historial con filtro de rango en fecha:
# Colección: stock_historial
# Campos: hospital_id ASC, fecha DESC
# (Si se agrega filtro por componente: hospital_id ASC, componente ASC, fecha DESC)

COLECCIONES_COMPONENTE = {
    "globulos_rojos": "globulos_rojos",
    "plasma": "plasma",
    "plaquetas": "plaquetas",
}
COLECCION_UMBRALES = "stock_umbrales"


def _col(componente: str):
    nombre = COLECCIONES_COMPONENTE.get(componente)
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Componente inválido: {componente}",
        )
    return db.collection(nombre)


def _doc_to_unidad(doc) -> UnidadOut:
    data = doc.to_dict() or {}
    return UnidadOut(
        id=doc.id,
        hospital_id=data["hospital_id"],
        blood_group=data["blood_group"],
        fecha_creacion=data["fecha_creacion"],
        fecha_vencimiento=data["fecha_vencimiento"],
        estado=data["estado"],
        turno_id=data.get("turno_id"),
        donante_id=data.get("donante_id"),
        motivo=data.get("motivo"),
        motivo_detalle=data.get("motivo_detalle"),
    )


# ─── CRUD de unidades ─────────────────────────────────────────────────────────

def crear_unidad_service(componente: str, hospital_id: str, body: UnidadCreate) -> UnidadOut:
    """
    hospital_id viene del token autenticado, no del body del request.
    """
    ahora = datetime.now(tz=timezone.utc)
    dias = VIDA_UTIL_DIAS[componente]
    vencimiento = ahora + timedelta(days=dias)

    payload = {
        "hospital_id": hospital_id,
        "blood_group": body.blood_group,
        "fecha_creacion": ahora,
        "fecha_vencimiento": vencimiento,
        "estado": "disponible",
        "turno_id": body.turno_id,
        "donante_id": body.donante_id,
    }

    _, ref = _col(componente).add(payload)
    doc = ref.get()
    return _doc_to_unidad(doc)


def listar_unidades_service(
    componente: str,
    hospital_id: Optional[str] = None,
    blood_group: Optional[str] = None,
    estado: Optional[str] = None,
) -> List[UnidadOut]:
    query = _col(componente)

    if hospital_id:
        query = query.where("hospital_id", "==", hospital_id)
    if blood_group:
        query = query.where("blood_group", "==", blood_group)
    if estado:
        query = query.where("estado", "==", estado)

    docs = query.stream()
    return [_doc_to_unidad(d) for d in docs]


def obtener_unidad_service(componente: str, unidad_id: str) -> UnidadOut:
    doc = _col(componente).document(unidad_id).get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidad {unidad_id} no encontrada en {componente}",
        )
    return _doc_to_unidad(doc)


def actualizar_unidad_service(componente: str, unidad_id: str, body: UnidadPatch) -> UnidadOut:
    ref = _col(componente).document(unidad_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidad {unidad_id} no encontrada en {componente}",
        )
    ref.update({"estado": body.estado})
    return _doc_to_unidad(ref.get())


def eliminar_unidad_service(componente: str, unidad_id: str) -> None:
    ref = _col(componente).document(unidad_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidad {unidad_id} no encontrada en {componente}",
        )
    ref.delete()


# ─── Resumen ──────────────────────────────────────────────────────────────────

def resumen_service(componente: str, hospital_id: str) -> ResumenOut:
    # Filtramos por hospital_id + estado=disponible.
    # El índice compuesto hospital_id+estado es suficiente para esta query.
    # Si se quiere filtrar también por blood_group en Firestore se necesitaría
    # un índice compuesto de 3 campos; aquí hacemos el agrupado en Python.
    docs = (
        _col(componente)
        .where("hospital_id", "==", hospital_id)
        .where("estado", "==", "disponible")
        .stream()
    )

    conteo: dict = {}
    for doc in docs:
        data = doc.to_dict() or {}
        bg = data.get("blood_group", "desconocido")
        conteo[bg] = conteo.get(bg, 0) + 1

    return ResumenOut(
        hospital_id=hospital_id,
        componente=componente,  # type: ignore[arg-type]
        disponibles_por_grupo=conteo,
    )


# ─── Acciones semánticas ──────────────────────────────────────────────────────

def _verificar_ownership_unidad(doc, componente: str, unidad_id: str, hospital_id: str) -> None:
    """Lanza 403 si la unidad no pertenece al hospital del usuario autenticado."""
    data = doc.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"La unidad {unidad_id} no pertenece a este hospital",
        )


def marcar_usado_service(
    componente: str,
    unidad_id: str,
    hospital_id: str,
    motivo: Optional[str] = None,
    motivo_detalle: Optional[str] = None,
) -> UnidadOut:
    """Marca una unidad como 'usado'. Verifica que pertenezca al hospital autenticado."""
    ref = _col(componente).document(unidad_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidad {unidad_id} no encontrada en {componente}",
        )
    _verificar_ownership_unidad(doc, componente, unidad_id, hospital_id)
    patch: dict = {"estado": "usado"}
    if motivo:
        patch["motivo"] = motivo
    if motivo_detalle:
        patch["motivo_detalle"] = motivo_detalle
    ref.update(patch)
    return _doc_to_unidad(ref.get())


def marcar_vencido_service(componente: str, unidad_id: str, hospital_id: str) -> UnidadOut:
    """Marca una unidad como 'vencido'. Verifica que pertenezca al hospital autenticado."""
    ref = _col(componente).document(unidad_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unidad {unidad_id} no encontrada en {componente}",
        )
    _verificar_ownership_unidad(doc, componente, unidad_id, hospital_id)
    ref.update({"estado": "vencido"})
    return _doc_to_unidad(ref.get())


def listar_disponibles_service(
    componente: str,
    hospital_id: Optional[str] = None,
    blood_group: Optional[str] = None,
) -> List[UnidadOut]:
    """Lista solo las unidades con estado 'disponible'."""
    query = _col(componente).where("estado", "==", "disponible")
    if hospital_id:
        query = query.where("hospital_id", "==", hospital_id)
    if blood_group:
        query = query.where("blood_group", "==", blood_group)
    return [_doc_to_unidad(d) for d in query.stream()]


def agregar_bulk_service(
    componente: str,
    hospital_id: str,
    blood_group: str,
    cantidad: int,
) -> List[UnidadOut]:
    """Crea N unidades del mismo componente y grupo sanguíneo. Devuelve la lista creada."""
    ahora = datetime.now(tz=timezone.utc)
    dias = VIDA_UTIL_DIAS[componente]
    vencimiento = ahora + timedelta(days=dias)

    payload = {
        "hospital_id": hospital_id,
        "blood_group": blood_group,
        "fecha_creacion": ahora,
        "fecha_vencimiento": vencimiento,
        "estado": "disponible",
        "turno_id": None,
        "donante_id": None,
    }

    unidades = []
    for _ in range(cantidad):
        _, ref = _col(componente).add(payload)
        doc = ref.get()
        unidades.append(_doc_to_unidad(doc))

    return unidades


def marcar_usado_bulk_service(
    componente: str,
    unidad_ids: List[str],
    hospital_id: str,
    motivo: Optional[str] = None,
    motivo_detalle: Optional[str] = None,
) -> List[UnidadOut]:
    """Marca múltiples unidades como 'usado'. Verifica ownership de cada una."""
    return [
        marcar_usado_service(componente, uid, hospital_id, motivo, motivo_detalle)
        for uid in unidad_ids
    ]


# ─── Historial de movimientos ─────────────────────────────────────────────────

def registrar_historial_service(
    hospital_id: str,
    usuario_id: str,
    usuario_nombre: str,
    accion: str,
    componente: str,
    blood_group: str,
    unidades_ids: List[str],
    cantidad: int,
    motivo: Optional[str] = None,
    motivo_detalle: Optional[str] = None,
) -> None:
    """Registra un movimiento de stock en la colección stock_historial."""
    db.collection(COLECCION_HISTORIAL).add({
        "hospital_id": hospital_id,
        "usuario_id": usuario_id,
        "usuario_nombre": usuario_nombre,
        "accion": accion,
        "componente": componente,
        "blood_group": blood_group,
        "unidades_ids": unidades_ids,
        "cantidad": cantidad,
        "motivo": motivo,
        "motivo_detalle": motivo_detalle,
        "fecha": datetime.now(tz=timezone.utc),
    })


def listar_historial_service(
    hospital_id: str,
    componente: Optional[str] = None,
    accion: Optional[str] = None,
    desde: Optional[datetime] = None,
    hasta: Optional[datetime] = None,
) -> List[HistorialOut]:
    """Lista el historial de movimientos del hospital, ordenado por fecha descendente."""
    query = db.collection(COLECCION_HISTORIAL).where("hospital_id", "==", hospital_id)

    if componente:
        query = query.where("componente", "==", componente)
    if accion:
        query = query.where("accion", "==", accion)
    if desde:
        query = query.where("fecha", ">=", desde)
    if hasta:
        query = query.where("fecha", "<=", hasta)

    docs = list(query.stream())

    resultado = []
    for doc in docs:
        data = doc.to_dict() or {}
        resultado.append(HistorialOut(
            id=doc.id,
            hospital_id=data["hospital_id"],
            usuario_id=data["usuario_id"],
            usuario_nombre=data["usuario_nombre"],
            accion=data["accion"],
            componente=data["componente"],
            blood_group=data["blood_group"],
            unidades_ids=data.get("unidades_ids", []),
            cantidad=data["cantidad"],
            motivo=data.get("motivo"),
            motivo_detalle=data.get("motivo_detalle"),
            fecha=data["fecha"],
        ))

    resultado.sort(key=lambda h: h.fecha, reverse=True)
    return resultado


# ─── Dashboard ────────────────────────────────────────────────────────────────

_TODOS_LOS_GRUPOS = _TODOS_LOS_GRUPOS_LIST


def dashboard_resumen_service(hospital_id: str) -> DashboardResumenOut:
    """
    Conteo de unidades disponibles por componente y grupo sanguíneo.
    Siempre devuelve todos los grupos (0 si no hay unidades).
    """
    resultado: dict = {}

    for componente in ("globulos_rojos", "plasma", "plaquetas"):
        docs = (
            _col(componente)
            .where("hospital_id", "==", hospital_id)
            .where("estado", "==", "disponible")
            .stream()
        )

        conteo: dict = {bg: 0 for bg in _TODOS_LOS_GRUPOS}
        for doc in docs:
            data = doc.to_dict() or {}
            bg = data.get("blood_group")
            if bg in conteo:
                conteo[bg] += 1

        conteo["total"] = sum(conteo.values())
        resultado[componente] = conteo

    return DashboardResumenOut(**resultado)


# ─── Totales disponibles ─────────────────────────────────────────────────────

def totales_disponibles_service(hospital_id: str) -> TotalesOut:
    """Cuenta documentos con estado='disponible' en las tres colecciones del hospital."""
    conteos = {}
    for componente in ("globulos_rojos", "plasma", "plaquetas"):
        docs = (
            _col(componente)
            .where("hospital_id", "==", hospital_id)
            .where("estado", "==", "disponible")
            .stream()
        )
        conteos[componente] = sum(1 for _ in docs)

    return TotalesOut(
        total=sum(conteos.values()),
        globulos_rojos=conteos["globulos_rojos"],
        plasma=conteos["plasma"],
        plaquetas=conteos["plaquetas"],
    )


# ─── Umbrales ─────────────────────────────────────────────────────────────────

def _doc_to_umbral(doc) -> UmbralOut:
    data = doc.to_dict() or {}
    return UmbralOut(
        id=doc.id,
        hospital_id=data["hospital_id"],
        componente=data["componente"],
        blood_group=data["blood_group"],
        umbral_minimo=data["umbral_minimo"],
    )


def listar_umbrales_service(hospital_id: str) -> List[UmbralOut]:
    docs = (
        db.collection(COLECCION_UMBRALES)
        .where("hospital_id", "==", hospital_id)
        .stream()
    )
    return [_doc_to_umbral(d) for d in docs]


def crear_o_actualizar_umbral_service(hospital_id: str, body: UmbralCreate) -> UmbralOut:
    """
    Upsert de umbral. hospital_id viene del token, no del body.
    Si ya existe un umbral para (hospital_id, componente, blood_group), lo actualiza.
    """
    query = (
        db.collection(COLECCION_UMBRALES)
        .where("hospital_id", "==", hospital_id)
        .where("componente", "==", body.componente)
        .where("blood_group", "==", body.blood_group)
        .limit(1)
        .stream()
    )
    docs = list(query)

    payload = {
        "hospital_id": hospital_id,
        "componente": body.componente,
        "blood_group": body.blood_group,
        "umbral_minimo": body.umbral_minimo,
    }

    if docs:
        ref = docs[0].reference
        ref.update({"umbral_minimo": body.umbral_minimo})
        return _doc_to_umbral(ref.get())

    _, ref = db.collection(COLECCION_UMBRALES).add(payload)
    return _doc_to_umbral(ref.get())


def actualizar_umbral_service(umbral_id: str, hospital_id: str, body: UmbralPatch) -> UmbralOut:
    """Actualiza un umbral. Verifica que pertenezca al hospital autenticado."""
    ref = db.collection(COLECCION_UMBRALES).document(umbral_id)
    doc = ref.get()
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Umbral {umbral_id} no encontrado",
        )
    data = doc.to_dict() or {}
    if data.get("hospital_id") != hospital_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"El umbral {umbral_id} no pertenece a este hospital",
        )
    ref.update({"umbral_minimo": body.umbral_minimo})
    return _doc_to_umbral(ref.get())


def inicializar_umbrales_service(hospital_id: str) -> InicializarUmbralesOut:
    """
    Crea los 24 umbrales por defecto (3 componentes × 8 grupos sanguíneos)
    para el hospital indicado. Solo crea los que no existen; no toca los existentes.
    """
    creados = 0
    existentes = 0

    col = db.collection(COLECCION_UMBRALES)

    for componente, umbral_default in UMBRALES_DEFAULT.items():
        for blood_group in _TODOS_LOS_GRUPOS_LIST:
            # Verificar si ya existe
            docs = list(
                col.where("hospital_id", "==", hospital_id)
                .where("componente", "==", componente)
                .where("blood_group", "==", blood_group)
                .limit(1)
                .stream()
            )

            if docs:
                existentes += 1
            else:
                col.add({
                    "hospital_id": hospital_id,
                    "componente": componente,
                    "blood_group": blood_group,
                    "umbral_minimo": umbral_default,
                })
                creados += 1

    return InicializarUmbralesOut(
        hospital_id=hospital_id,
        umbrales_creados=creados,
        umbrales_existentes=existentes,
    )
