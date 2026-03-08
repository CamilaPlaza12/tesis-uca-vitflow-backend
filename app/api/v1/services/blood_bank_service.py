from fastapi import HTTPException
from google.cloud import firestore
from google.cloud.firestore import Transaction

from app.api.v1.services.hospital_request_service import (
    find_active_auto_request_by_blood_group_service,
    create_auto_low_stock_request_service,
)

from app.firebase.firebase_client import db
from app.schemas.blood_bank_schema import (
    DEFAULT_STOCKS,
    DEFAULT_THRESHOLDS,
    BloodBankOut,
    BloodBankAdjustRequest,
    BloodBankThresholdsUpdateRequest,
)

BLOOD_BANKS_COLLECTION = "blood_banks"

def _bank_ref(hospital_id: str):
    return db.collection(BLOOD_BANKS_COLLECTION).document(hospital_id)

def ensure_auto_request_if_low_service(hospital_id: str, blood_group: str):
    """
    Si stock <= threshold para ese blood_group:
    - si NO existe request ACTIVO con requested_by="Sistema" -> crea uno URGENTE
    """
    ref = _bank_ref(hospital_id)
    snap = ref.get()
    if not snap.exists:
        return

    data = snap.to_dict() or {}
    stocks = data.get("stocks_ml") or {}
    thresholds = data.get("thresholds_ml") or {}

    # si el hospital no definió threshold para ese RH -> NO hacemos nada
    if blood_group not in thresholds:
        return

    try:
        stock_ml = int(stocks.get(blood_group, 0) or 0)
        thr_ml = int(thresholds.get(blood_group, 0) or 0)
    except Exception:
        return
    
    if thr_ml <= 0:
        return
    
    if stock_ml >= thr_ml:
        return

    existing = find_active_auto_request_by_blood_group_service(hospital_id, blood_group)
    if existing:
        return

    missing_ml = thr_ml - stock_ml
    if missing_ml <= 0:
        return

    requested_liters = missing_ml / 1000.0  # EXACTO lo que falta

    create_auto_low_stock_request_service(
        hospital_id,
        blood_group,
        requested_liters=requested_liters,
    )




def get_or_create_blood_bank_service(hospital_id: str) -> BloodBankOut:
    ref = _bank_ref(hospital_id)
    snap = ref.get()

    if not snap.exists:
        payload = {
            "hospital_id": hospital_id,
            "stocks_ml": DEFAULT_STOCKS,
            "thresholds_ml": DEFAULT_THRESHOLDS}
        ref.set(payload, merge=False)
        return BloodBankOut(**payload)

    data = snap.to_dict() or {}
    stocks = data.get("stocks_ml") or {}

    # backstop: asegurar que estén todas las keys
    fixed = dict(DEFAULT_STOCKS)
    for k, v in stocks.items():
        try:
            fixed[k] = int(v)
        except Exception:
            fixed[k] = 0
    
    thresholds = data.get("thresholds_ml") or {}
    fixed_thr = {}
    for k, v in thresholds.items():
        if k in DEFAULT_STOCKS:
            try:
                fixed_thr[k] = max(0, int(v))
            except Exception:
                pass


    payload = {"hospital_id": hospital_id, "stocks_ml": fixed, "thresholds_ml": fixed_thr}
    # opcional: si querés “autocurar” el doc
    if fixed != stocks:
        ref.set({"stocks_ml": fixed}, merge=True)


    return BloodBankOut(**payload)

def add_stock_service(hospital_id: str, body: BloodBankAdjustRequest) -> BloodBankOut:
    ref = _bank_ref(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)

        if not snap.exists:
            tx.set(ref, {"hospital_id": hospital_id, "stocks_ml": DEFAULT_STOCKS}, merge=False)
            current = dict(DEFAULT_STOCKS)
        else:
            data = snap.to_dict() or {}
            current = dict(DEFAULT_STOCKS)
            stored = data.get("stocks_ml") or {}
            for k, v in stored.items():
                if k in current:
                    current[k] = int(v or 0)

        bt = body.blood_type
        current[bt] = int(current.get(bt, 0)) + int(body.amount_ml)

        tx.update(ref, {"stocks_ml": current})
        return current

    tx = db.transaction()
    new_stocks = _tx(tx)
    ensure_auto_request_if_low_service(hospital_id, body.blood_type)
    return BloodBankOut(hospital_id=hospital_id, stocks_ml=new_stocks)

def remove_stock_service(hospital_id: str, body: BloodBankAdjustRequest) -> BloodBankOut:
    ref = _bank_ref(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)
        if not snap.exists:
            raise HTTPException(status_code=409, detail="El hospital no tiene banco de sangre inicializado")

        data = snap.to_dict() or {}
        current = dict(DEFAULT_STOCKS)
        stored = data.get("stocks_ml") or {}
        for k, v in stored.items():
            if k in current:
                current[k] = int(v or 0)

        bt = body.blood_type
        amount = int(body.amount_ml)
        prev = int(current.get(bt, 0))

        if prev - amount < 0:
            raise HTTPException(status_code=409, detail=f"No hay stock suficiente en {bt} (stock={prev}ml)")

        current[bt] = prev - amount
        tx.update(ref, {"stocks_ml": current})
        return current

    tx = db.transaction()
    new_stocks = _tx(tx)
    ensure_auto_request_if_low_service(hospital_id, body.blood_type)
    return BloodBankOut(hospital_id=hospital_id, stocks_ml=new_stocks)


def add_blood_ml_by_group_service(hospital_id: str, blood_group: str, amount_ml: int) -> dict:
    if not blood_group or blood_group not in DEFAULT_STOCKS:
        raise HTTPException(status_code=409, detail=f"Invalid blood_group '{blood_group}'")

    if amount_ml <= 0:
        raise HTTPException(status_code=400, detail="amount_ml must be > 0")

    ref = db.collection(BLOOD_BANKS_COLLECTION).document(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)

        if not snap.exists:
            tx.set(ref, {"hospital_id": hospital_id, "stocks_ml": DEFAULT_STOCKS}, merge=False)
            current = dict(DEFAULT_STOCKS)
        else:
            data = snap.to_dict() or {}
            stored = data.get("stocks_ml") or {}
            current = dict(DEFAULT_STOCKS)
            for k, v in stored.items():
                if k in current:
                    current[k] = int(v or 0)

        current[blood_group] = int(current.get(blood_group, 0)) + int(amount_ml)
        tx.update(ref, {"stocks_ml": current})
        return current

    tx = db.transaction()
    new_stocks = _tx(tx)
    ensure_auto_request_if_low_service(hospital_id, blood_group)
    return {"hospital_id": hospital_id, "stocks_ml": new_stocks}

def update_thresholds_service(hospital_id: str, body: BloodBankThresholdsUpdateRequest) -> BloodBankOut:
    ref = _bank_ref(hospital_id)

    @firestore.transactional
    def _tx(tx: Transaction):
        snap = ref.get(transaction=tx)

        # si no existe, inicializamos
        if not snap.exists:
            tx.set(ref, {"hospital_id": hospital_id, "stocks_ml": DEFAULT_STOCKS, "thresholds_ml": DEFAULT_THRESHOLDS}, merge=False)
            current_stocks = dict(DEFAULT_STOCKS)
            current_thr = dict(DEFAULT_THRESHOLDS)
        else:
            data = snap.to_dict() or {}

            # stocks (backstop)
            current_stocks = dict(DEFAULT_STOCKS)
            stored_stocks = data.get("stocks_ml") or {}
            for k, v in stored_stocks.items():
                if k in current_stocks:
                    try:
                        current_stocks[k] = int(v or 0)
                    except Exception:
                        current_stocks[k] = 0

            # thresholds existentes
            stored_thr = data.get("thresholds_ml") or {}
            current_thr = {}
            for k, v in stored_thr.items():
                if k in DEFAULT_STOCKS:
                    try:
                        current_thr[k] = max(0, int(v))
                    except Exception:
                        pass

        # merge parcial con lo que manda el hospital
        for bg, thr in (body.thresholds_ml or {}).items():
            current_thr[bg] = int(thr)

        tx.update(ref, {"thresholds_ml": current_thr})
        return current_stocks, current_thr

    tx = db.transaction()
    stocks, thresholds = _tx(tx)
    return BloodBankOut(hospital_id=hospital_id, stocks_ml=stocks, thresholds_ml=thresholds)

