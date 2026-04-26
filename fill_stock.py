"""
fill_stock.py — Rellena el stock del hospital hasta superar el umbral mínimo.

Uso:
    python fill_stock.py

Por cada componente × grupo sanguíneo, verifica cuántas unidades
disponibles hay y agrega las necesarias para llegar a TARGET_UNITS (6).
Es idempotente: si ya hay suficientes, no agrega nada.
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from app.firebase import firebase_client  # noqa: F401
from app.firebase.firebase_client import db

HOSPITAL_ID = "VUJW2Vwz23KRETik4Uxz"
TARGET_UNITS = 6  # por encima del umbral mínimo de 5

COMPONENTES = ["globulos_rojos", "plasma", "plaquetas"]
GRUPOS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

VIDA_UTIL_DIAS = {
    "globulos_rojos": 42,
    "plasma": 365,
    "plaquetas": 5,
}


def contar_disponibles(componente: str, blood_group: str) -> int:
    docs = (
        db.collection(componente)
        .where("hospital_id", "==", HOSPITAL_ID)
        .where("blood_group", "==", blood_group)
        .where("estado", "==", "disponible")
        .stream()
    )
    return sum(1 for _ in docs)


def agregar_unidades(componente: str, blood_group: str, cantidad: int) -> None:
    ahora = datetime.now(tz=timezone.utc)
    vencimiento = ahora + timedelta(days=VIDA_UTIL_DIAS[componente])
    col = db.collection(componente)
    for _ in range(cantidad):
        col.add({
            "hospital_id": HOSPITAL_ID,
            "blood_group": blood_group,
            "fecha_creacion": ahora,
            "fecha_vencimiento": vencimiento,
            "estado": "disponible",
            "turno_id": None,
            "donante_id": None,
        })


def main():
    print("=" * 60)
    print(f"  VitFlow — Fill stock hospital {HOSPITAL_ID}")
    print(f"  Objetivo: >= {TARGET_UNITS} unidades por grupo/componente (umbral minimo = 5)")
    print("=" * 60)

    total_agregadas = 0

    for componente in COMPONENTES:
        print(f"\n-- {componente} --")
        for grupo in GRUPOS:
            actuales = contar_disponibles(componente, grupo)
            faltantes = max(0, TARGET_UNITS - actuales)
            if faltantes > 0:
                agregar_unidades(componente, grupo, faltantes)
                print(f"  {grupo:4s}  tenia {actuales} -> agregadas {faltantes} -> total {actuales + faltantes}")
                total_agregadas += faltantes
            else:
                print(f"  {grupo:4s}  tenia {actuales} -> OK (no se agrega nada)")

    print("\n" + "=" * 60)
    print(f"  Total unidades agregadas: {total_agregadas}")
    print("=" * 60)
    if total_agregadas > 0:
        print("\n[OK] Stock rellenado.")
    else:
        print("\n[OK] El stock ya estaba por encima del umbral — no se agregó nada.")


if __name__ == "__main__":
    main()
