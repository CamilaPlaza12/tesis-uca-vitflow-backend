"""
Seed: 5 turnos para el pedido tipo EVENTO vqI6l2lGPNvT8oovrvYW el 27/04/2026.
Crea donantes ficticios si no hay suficientes en la colección.

Uso:
  python -m scripts.seed_turnos_evento
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.firebase.firebase_client import db

PEDIDO_ID = "vqI6l2lGPNvT8oovrvYW"
DATE_LOCAL = "2026-04-27"
HORARIOS = ["09:00", "10:30", "12:00", "14:00", "15:30"]

DONORS_SEED = [
    {"first_name": "Lucas",    "last_name": "Fernández",  "dni": "38111001", "blood_group": "O+"},
    {"first_name": "Valentina","last_name": "Gómez",      "dni": "39222002", "blood_group": "A+"},
    {"first_name": "Mateo",    "last_name": "Rodríguez",  "dni": "40333003", "blood_group": "B+"},
    {"first_name": "Sofía",    "last_name": "López",      "dni": "41444004", "blood_group": "AB-"},
    {"first_name": "Tomás",    "last_name": "Martínez",   "dni": "42555005", "blood_group": "O-"},
]


def get_pedido() -> dict:
    snap = db.collection("hospital_requests").document(PEDIDO_ID).get()
    if not snap.exists:
        raise SystemExit(f"❌  Pedido {PEDIDO_ID} no encontrado en Firestore")
    data = snap.to_dict() or {}
    data["id"] = snap.id
    return data


def get_or_create_donors(needed: int) -> list[dict]:
    """Devuelve hasta `needed` donantes. Crea ficticios si faltan."""
    docs = list(db.collection("donors").limit(needed).stream())
    donors: list[dict] = []

    for doc in docs:
        d = doc.to_dict() or {}
        d["id"] = doc.id
        donors.append(d)

    while len(donors) < needed:
        idx = len(donors)
        seed = DONORS_SEED[idx]
        dni = seed["dni"]

        # Evitar duplicados por DNI
        existing = list(
            db.collection("donors").where("dni", "==", dni).limit(1).stream()
        )
        if existing:
            d = existing[0].to_dict() or {}
            d["id"] = existing[0].id
            donors.append(d)
            continue

        doc_data = {
            "first_name": seed["first_name"],
            "last_name":  seed["last_name"],
            "dni":        dni,
            "blood_group": seed["blood_group"],
            "email":      f"{seed['first_name'].lower()}.{seed['last_name'].lower()}@seed.test",
            "phone_number": "+541100000000",
            "gender":     "M",
            "birth_date": "1995-06-15",
            "weight_kg":  70.0,
            "address_text": "Av. Corrientes 1234, Buenos Aires",
            "is_subscribed": True,
            "has_consent": True,
            "is_enabled":  True,
            "has_recent_tattoo": False,
            "has_fever_or_infection": False,
        }
        _, ref = db.collection("donors").add(doc_data)
        doc_data["id"] = ref.id
        donors.append(doc_data)
        print(f"  [+] Donante creado: {seed['first_name']} {seed['last_name']} (DNI {dni}) -> {ref.id}")

    return donors[:needed]


def create_appointment(pedido: dict, donor: dict, horario: str) -> str:
    hospital_id = pedido["hospital_id"]
    donor_id    = donor["id"]
    first       = (donor.get("first_name") or "").strip()
    last        = (donor.get("last_name")  or "").strip()
    full_name   = f"{first} {last}".strip() or donor_id
    dni         = donor.get("dni", "")

    data = {
        "hospital_request_id": PEDIDO_ID,
        "hospital_id":         hospital_id,
        "donor_id":            donor_id,
        "date_local":          DATE_LOCAL,
        "time_local":          horario,
        "donor": {
            "full_name": full_name,
            "dni":       dni,
        },
        "donation_type": "SANGRE",
        "source":        "HOSPITAL_MANUAL",
        "status":        "PROGRAMADO",
    }

    _, ref = db.collection("appointments").add(data)
    return ref.id


def main():
    print(f"\n[*] Leyendo pedido {PEDIDO_ID}...")
    pedido = get_pedido()
    print(f"    hospital_id : {pedido['hospital_id']}")
    print(f"    request_type: {pedido.get('request_type')}")
    print(f"    status      : {pedido.get('status')}")

    print(f"\n[*] Obteniendo 5 donantes...")
    donors = get_or_create_donors(5)
    for d in donors:
        print(f"    - {d.get('first_name')} {d.get('last_name')} (DNI {d.get('dni')}) -> {d['id']}")

    print(f"\n[*] Creando turnos para el {DATE_LOCAL}...")
    for donor, horario in zip(donors, HORARIOS):
        appt_id = create_appointment(pedido, donor, horario)
        print(f"    OK  {horario}  {donor.get('first_name')} {donor.get('last_name')}  -> {appt_id}")

    print("\n[OK] 5 turnos creados correctamente.\n")


if __name__ == "__main__":
    main()
