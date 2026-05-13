from datetime import datetime
from app.firebase.firebase_client import db
from app.utils.geocoding import geocode_address_google
from app.api.v1.services.stock_service import inicializar_umbrales_service

COLLECTION = "hospitals"


def create_hospital_from_onboarding_request(
    request_id: str,
    req: dict,
) -> str:

    now = datetime.utcnow().isoformat()

    hospital = req.get("hospital", {})
    address = hospital.get("address", {})

    if not hospital.get("name"):
        raise Exception("Hospital name missing in onboarding request")

    # 🔵 Armamos dirección completa para geocoding
    street = address.get("street", "")
    number = address.get("number", "")
    city = address.get("city", "")
    localidad = address.get("localidad", "")
    province = address.get("province", "")

    full_address = f"{street} {number}, {localidad}, {city}, {province}, Argentina"

    geo = geocode_address_google(full_address)

    if geo is None:
        raise Exception("Could not geocode hospital address")

    hospital_data = {
        "name": hospital.get("name"),
        "email": hospital.get("email"),
        "phone": hospital.get("phone"),
        "address": address,
        "geo": geo,   # 👈 NUEVO
        "subscriptionStatus": "PENDING_PAYMENT",
        "createdAt": now,
        "createdFromRequestId": request_id,
    }

    res = db.collection(COLLECTION).add(hospital_data)
    ref = res[1] if isinstance(res, (list, tuple)) else res

    hospital_id = ref.id

    # Crear umbrales mínimos por defecto para los 3 componentes × 8 grupos sanguíneos
    inicializar_umbrales_service(hospital_id)

    return hospital_id