"""
seed.py — Poblar Firestore con datos de prueba para VitFlow.

Uso:
    source venv/bin/activate   (o venv\\Scripts\\activate en Windows)
    python seed.py

El script:
- Detecta automáticamente el primer hospital existente en Firestore.
- Si no hay hospitales, lo indica y no crea nada.
- Es idempotente: puede correrse varias veces sin duplicar datos.
  (las unidades de stock se identifican por un campo seed_id único)
- Al final imprime un resumen de lo creado vs omitido.
"""

import os
import sys
from datetime import datetime, timedelta, timezone, date

# ── Inicializar Firebase antes que nada ───────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

from app.firebase import firebase_client  # noqa: F401  — dispara initialize_app
from app.firebase.firebase_client import db

# ── Constantes ────────────────────────────────────────────────────────────────

VIDA_UTIL_DIAS = {
    "globulos_rojos": 42,
    "plasma": 365,
    "plaquetas": 5,
}

UMBRALES_DEFAULT = {
    "globulos_rojos": 5,
    "plasma": 3,
    "plaquetas": 2,
}

TODOS_LOS_GRUPOS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# Distribución de unidades de stock a crear
STOCK_SEED = {
    "globulos_rojos": [
        ("A+", 4), ("O+", 4), ("B+", 3), ("A-", 2), ("O-", 2),
    ],
    "plasma": [
        ("A+", 3), ("O+", 3), ("B+", 2), ("AB+", 2),
    ],
    "plaquetas": [
        ("O+", 3), ("A+", 2), ("B+", 1),
    ],
}

# Turnos a crear: (días_desde_hoy, blood_group, dni_ficticio, nombre_ficticio)
TURNOS_SEED = [
    (0,  "A+",  "12345678", "Ana García"),
    (0,  "O+",  "23456789", "Carlos López"),
    (1,  "B+",  "34567890", "María Fernández"),
    (1,  "A-",  "45678901", "Pedro Rodríguez"),
    (2,  "AB+", "56789012", "Laura Martínez"),
    (2,  "O-",  "67890123", "Diego Sánchez"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_hospital_id() -> str | None:
    """Devuelve el ID del primer hospital encontrado en Firestore."""
    docs = list(db.collection("hospitals").limit(1).stream())
    if not docs:
        return None
    return docs[0].id


def ahora_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def fecha_vencimiento(componente: str, desde: datetime) -> datetime:
    return desde + timedelta(days=VIDA_UTIL_DIAS[componente])


# ── Seed: stock ───────────────────────────────────────────────────────────────

def seed_stock(hospital_id: str) -> dict:
    """
    Crea unidades de stock para los tres componentes.
    Idempotencia: cada unidad tiene un campo 'seed_id' único.
    Si ya existe una unidad con ese seed_id, se omite.
    """
    creadas = 0
    omitidas = 0
    ahora = ahora_utc()

    for componente, grupos in STOCK_SEED.items():
        col = db.collection(componente)

        for blood_group, cantidad in grupos:
            for i in range(cantidad):
                seed_id = f"seed__{hospital_id}__{componente}__{blood_group}__{i}"

                # Verificar si ya existe
                existentes = list(
                    col.where("seed_id", "==", seed_id).limit(1).stream()
                )
                if existentes:
                    omitidas += 1
                    continue

                col.add({
                    "hospital_id": hospital_id,
                    "blood_group": blood_group,
                    "fecha_creacion": ahora,
                    "fecha_vencimiento": fecha_vencimiento(componente, ahora),
                    "estado": "disponible",
                    "turno_id": None,
                    "donante_id": None,
                    "seed_id": seed_id,  # solo para idempotencia del seed
                })
                creadas += 1

    return {"creadas": creadas, "omitidas": omitidas}


# ── Seed: turnos ──────────────────────────────────────────────────────────────

def seed_turnos(hospital_id: str) -> dict:
    """
    Crea turnos de prueba en la colección 'appointments'.
    Idempotencia: un turno de seed se identifica por seed_id.

    Nota: se escribe directo a Firestore sin pasar por reserve_slot_service
    (que valida disponibilidad/capacidad del hospital) ya que es solo para testing.
    slot_key se construye igual que en el servicio real.
    hospital_request_id se deja como 'seed_request' (referencia ficticia para testing).
    """
    creados = 0
    omitidos = 0
    hoy = date.today()
    col = db.collection("appointments")

    for dias_offset, blood_group, dni, nombre in TURNOS_SEED:
        fecha = hoy + timedelta(days=dias_offset)
        time_local = "09:00"
        seed_id = f"seed__appt__{hospital_id}__{fecha.isoformat()}__{dni}"

        # Verificar si ya existe
        existentes = list(
            col.where("seed_id", "==", seed_id).limit(1).stream()
        )
        if existentes:
            omitidos += 1
            continue

        slot_key = f"{hospital_id}_{fecha.isoformat()}_{time_local}"

        col.add({
            "hospital_id": hospital_id,
            "hospital_request_id": "seed_request",
            "date_local": fecha.isoformat(),
            "time_local": time_local,
            "donor": {
                "full_name": nombre,
                "dni": dni,
            },
            # blood_group del donante — campo informativo, no está en el schema
            # de Appointment pero sí se necesita para verificar la confirmación
            # de donación desde el frontend. Se agrega como campo extra.
            "blood_group": blood_group,
            "donation_type": "SANGRE",
            "status": "PROGRAMADO",
            "source": "HOSPITAL_MANUAL",
            "slot_key": slot_key,
            "seed_id": seed_id,
        })
        creados += 1

    return {"creados": creados, "omitidos": omitidos}


# ── Seed: umbrales ────────────────────────────────────────────────────────────

def seed_umbrales(hospital_id: str) -> dict:
    """
    Inicializa los 24 umbrales por defecto para el hospital.
    Usa la misma lógica que POST /stock/umbrales/inicializar:
    solo crea los que no existen.
    """
    creados = 0
    omitidos = 0
    col = db.collection("stock_umbrales")

    for componente, umbral_default in UMBRALES_DEFAULT.items():
        for blood_group in TODOS_LOS_GRUPOS:
            existentes = list(
                col.where("hospital_id", "==", hospital_id)
                .where("componente", "==", componente)
                .where("blood_group", "==", blood_group)
                .limit(1)
                .stream()
            )
            if existentes:
                omitidos += 1
                continue

            col.add({
                "hospital_id": hospital_id,
                "componente": componente,
                "blood_group": blood_group,
                "umbral_minimo": umbral_default,
            })
            creados += 1

    return {"creados": creados, "omitidos": omitidos}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  VitFlow — Seed de datos de prueba")
    print("=" * 55)

    # 1. Detectar hospital
    hospital_id = get_hospital_id()
    if not hospital_id:
        print("\n[ERROR] No se encontró ningún hospital en Firestore.")
        print("        Completá el onboarding de al menos un hospital antes de correr el seed.")
        sys.exit(1)

    print(f"\nHospital detectado: {hospital_id}")

    # 2. Stock
    print("\n── Stock de componentes ──")
    res_stock = seed_stock(hospital_id)
    total_stock = sum(c for _, grupos in STOCK_SEED.items() for _, c in grupos)
    print(f"  Unidades a crear:  {total_stock}")
    print(f"  Creadas:           {res_stock['creadas']}")
    print(f"  Omitidas (ya existían): {res_stock['omitidas']}")

    # 3. Turnos
    print("\n── Turnos de donación ──")
    res_turnos = seed_turnos(hospital_id)
    print(f"  Turnos a crear:    {len(TURNOS_SEED)}")
    print(f"  Creados:           {res_turnos['creados']}")
    print(f"  Omitidos (ya existían): {res_turnos['omitidos']}")

    # Detalle de fechas
    hoy = date.today()
    print(f"    Hoy ({hoy.isoformat()}):              A+, O+  — 09:00")
    print(f"    Mañana ({(hoy + timedelta(1)).isoformat()}):         B+, A-  — 09:00")
    print(f"    Pasado mañana ({(hoy + timedelta(2)).isoformat()}): AB+, O- — 09:00")

    # 4. Umbrales
    print("\n── Umbrales mínimos ──")
    res_umbrales = seed_umbrales(hospital_id)
    print(f"  Umbrales a crear:  24  (3 componentes × 8 grupos)")
    print(f"  Creados:           {res_umbrales['creados']}")
    print(f"  Omitidos (ya existían): {res_umbrales['omitidos']}")

    # 5. Resumen final
    print("\n" + "=" * 55)
    total_creado = res_stock["creadas"] + res_turnos["creados"] + res_umbrales["creados"]
    total_omitido = res_stock["omitidas"] + res_turnos["omitidos"] + res_umbrales["omitidos"]
    print(f"  Total documentos creados:  {total_creado}")
    print(f"  Total omitidos:            {total_omitido}")
    print("=" * 55)

    if total_creado > 0:
        print("\n[OK] Seed completado.")
    else:
        print("\n[OK] El seed ya había corrido — no se duplicó nada.")


if __name__ == "__main__":
    main()
