import logging

from fastapi import HTTPException
from google.cloud import firestore
from google.cloud.firestore import Transaction

from app.api.v1.services.hospital_request_service import (
    find_active_auto_request_by_blood_group_service,
    create_auto_low_stock_request_service,
    process_expired_auto_requests_service,
)
from app.api.v1.services.vito_notification_service import notify_vito_for_new_request

logger = logging.getLogger("vitflow.blood_bank")

from app.firebase.firebase_client import db
from app.schemas.blood_bank_schema import (
    DEFAULT_STOCKS,
    DEFAULT_THRESHOLDS,
    BloodBankOut,
    BloodBankAdjustRequest,
    BloodBankThresholdsUpdateRequest,
)

BLOOD_BANKS_COLLECTION = "blood_banks"
COLECCION_UMBRALES = "stock_umbrales"

def _bank_ref(hospital_id: str):
    return db.collection(BLOOD_BANKS_COLLECTION).document(hospital_id)

def ensure_auto_request_if_low_service(hospital_id: str, componente: str, blood_group: str):
    """
    Si las unidades disponibles de `componente` + `blood_group` < umbral_minimo configurado:
    - si NO existe request ACTIVO del Sistema para ese componente+grupo → crea uno URGENTE de 5 días
    Funciona para globulos_rojos, plasma y plaquetas.
    """
    umbral_docs = list(
        db.collection(COLECCION_UMBRALES)
        .where("hospital_id", "==", hospital_id)
        .where("componente", "==", componente)
        .where("blood_group", "==", blood_group)
        .limit(1)
        .stream()
    )
    if not umbral_docs:
        logger.info("[AUTO-REQUEST] no hay umbral para %s/%s/%s → skip", hospital_id, componente, blood_group)
        return

    umbral_minimo = int((umbral_docs[0].to_dict() or {}).get("umbral_minimo", 0) or 0)
    if umbral_minimo <= 0:
        logger.info("[AUTO-REQUEST] umbral_minimo=0 para %s/%s/%s → skip", hospital_id, componente, blood_group)
        return

    stock_count = len(list(
        db.collection(componente)
        .where("hospital_id", "==", hospital_id)
        .where("blood_group", "==", blood_group)
        .where("estado", "==", "disponible")
        .stream()
    ))

    logger.info("[AUTO-REQUEST] hospital=%s componente=%s blood_group=%s disponibles=%d umbral=%d",
                hospital_id, componente, blood_group, stock_count, umbral_minimo)

    if stock_count >= umbral_minimo:
        logger.info("[AUTO-REQUEST] disponibles(%d) >= umbral(%d) → skip", stock_count, umbral_minimo)
        return

    process_expired_auto_requests_service(hospital_id, blood_group, componente)

    existing = find_active_auto_request_by_blood_group_service(hospital_id, blood_group, componente)
    if existing:
        logger.info("[AUTO-REQUEST] ya existe pedido activo id=%s → skip", existing.get("id"))
        return

    logger.info("[AUTO-REQUEST] creando pedido para %s/%s/%s (disponibles=%d < umbral=%d)",
                hospital_id, componente, blood_group, stock_count, umbral_minimo)
    new_request = create_auto_low_stock_request_service(hospital_id, blood_group, componente)
    notify_vito_for_new_request(hospital_id, new_request["id"])




def get_or_create_blood_bank_service(hospital_id: str) -> BloodBankOut:
    ref = _bank_ref(hospital_id)
    snap = ref.get()

    if not snap.exists:
        payload = {
            "hospital_id": hospital_id,
            "stocks_units": DEFAULT_STOCKS,
            "thresholds_units": DEFAULT_THRESHOLDS}
        ref.set(payload, merge=False)
        return BloodBankOut(**payload)

    data = snap.to_dict() or {}
    stocks = data.get("stocks_units") or {}

    # backstop: asegurar que estén todas las keys
    fixed = dict(DEFAULT_STOCKS)
    for k, v in stocks.items():
        try:
            fixed[k] = int(v)
        except Exception:
            fixed[k] = 0
    
    thresholds = data.get("thresholds_units") or {}
    fixed_thr = {}
    for k, v in thresholds.items():
        if k in DEFAULT_STOCKS:
            try:
                fixed_thr[k] = max(0, int(v))
            except Exception:
                pass


    payload = {"hospital_id": hospital_id, "stocks_units": fixed, "thresholds_units": fixed_thr}
    # opcional: si querés “autocurar” el doc
    if fixed != stocks:
        ref.set({"stocks_units": fixed}, merge=True)


    return BloodBankOut(**payload)

def add_stock_service(hospital_id: str, body: BloodBankAdjustRequest) -> BloodBankOut:
    ref = _bank_ref(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)

        if not snap.exists:
            tx.set(ref, {"hospital_id": hospital_id, "stocks_units": DEFAULT_STOCKS}, merge=False)
            current = dict(DEFAULT_STOCKS)
        else:
            data = snap.to_dict() or {}
            current = dict(DEFAULT_STOCKS)
            stored = data.get("stocks_units") or {}
            for k, v in stored.items():
                if k in current:
                    current[k] = int(v or 0)

        bt = body.blood_type
        current[bt] = int(current.get(bt, 0)) + int(body.amount_units)

        tx.update(ref, {"stocks_units": current})
        return current

    tx = db.transaction()
    new_stocks = _tx(tx)
    return BloodBankOut(hospital_id=hospital_id, stocks_units=new_stocks)

def remove_stock_service(hospital_id: str, body: BloodBankAdjustRequest) -> BloodBankOut:
    ref = _bank_ref(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)
        if not snap.exists:
            raise HTTPException(status_code=409, detail="El hospital no tiene banco de sangre inicializado")

        data = snap.to_dict() or {}
        current = dict(DEFAULT_STOCKS)
        stored = data.get("stocks_units") or {}
        for k, v in stored.items():
            if k in current:
                current[k] = int(v or 0)

        bt = body.blood_type
        amount = int(body.amount_units)
        prev = int(current.get(bt, 0))

        if prev - amount < 0:
            raise HTTPException(status_code=409, detail=f"No hay stock suficiente en {bt} (stock={prev}units)")

        current[bt] = prev - amount
        tx.update(ref, {"stocks_units": current})
        return current

    tx = db.transaction()
    new_stocks = _tx(tx)
    return BloodBankOut(hospital_id=hospital_id, stocks_units=new_stocks)


def add_blood_units_by_group_service(hospital_id: str, blood_group: str, amount_units: int) -> dict:
    if not blood_group or blood_group not in DEFAULT_STOCKS:
        raise HTTPException(status_code=409, detail=f"Invalid blood_group '{blood_group}'")

    if amount_units <= 0:
        raise HTTPException(status_code=400, detail="amount_units must be > 0")

    ref = db.collection(BLOOD_BANKS_COLLECTION).document(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)

        if not snap.exists:
            tx.set(ref, {"hospital_id": hospital_id, "stocks_units": DEFAULT_STOCKS}, merge=False)
            current = dict(DEFAULT_STOCKS)
        else:
            data = snap.to_dict() or {}
            stored = data.get("stocks_units") or {}
            current = dict(DEFAULT_STOCKS)
            for k, v in stored.items():
                if k in current:
                    current[k] = int(v or 0)

        current[blood_group] = int(current.get(blood_group, 0)) + int(amount_units)
        tx.update(ref, {"stocks_units": current})
        return current

    tx = db.transaction()
    new_stocks = _tx(tx)
    return {"hospital_id": hospital_id, "stocks_units": new_stocks}

def update_thresholds_service(hospital_id: str, body: BloodBankThresholdsUpdateRequest) -> BloodBankOut:
    ref = _bank_ref(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)

        # si no existe, inicializamos
        if not snap.exists:
            tx.set(ref, {"hospital_id": hospital_id, "stocks_units": DEFAULT_STOCKS, "thresholds_units": DEFAULT_THRESHOLDS}, merge=False)
            current_stocks = dict(DEFAULT_STOCKS)
            current_thr = dict(DEFAULT_THRESHOLDS)
        else:
            data = snap.to_dict() or {}

            # stocks (backstop)
            current_stocks = dict(DEFAULT_STOCKS)
            stored_stocks = data.get("stocks_units") or {}
            for k, v in stored_stocks.items():
                if k in current_stocks:
                    try:
                        current_stocks[k] = int(v or 0)
                    except Exception:
                        current_stocks[k] = 0

            # thresholds existentes
            stored_thr = data.get("thresholds_units") or {}
            current_thr = {}
            for k, v in stored_thr.items():
                if k in DEFAULT_STOCKS:
                    try:
                        current_thr[k] = max(0, int(v))
                    except Exception:
                        pass

        # merge parcial con lo que manda el hospital
        for bg, thr in (body.thresholds_units or {}).items():
            current_thr[bg] = int(thr)

        tx.update(ref, {"thresholds_units": current_thr})
        return current_stocks, current_thr

    tx = db.transaction()
    stocks, thresholds = _tx(tx)
    return BloodBankOut(hospital_id=hospital_id, stocks_units=stocks, thresholds_units=thresholds)

