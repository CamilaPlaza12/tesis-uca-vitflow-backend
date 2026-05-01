"""
Migración: agrega blood_group al embed donor en todos los turnos existentes.

Por cada turno que no tenga donor.blood_group definido, busca al donante
por donor_id (o por donor.dni como fallback) y actualiza el embed.

Uso:
  python -m scripts.migrate_donor_blood_group
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.firebase.firebase_client import db

def get_donor_blood_group(donor_id: str | None, dni: str | None) -> str | None:
    if donor_id:
        doc = db.collection("donors").document(donor_id).get()
        if doc.exists:
            return (doc.to_dict() or {}).get("blood_group")

    if dni:
        docs = db.collection("donors").where("dni", "==", dni).limit(1).stream()
        for d in docs:
            return (d.to_dict() or {}).get("blood_group")

    return None


def run():
    print("Leyendo turnos...")
    all_appointments = list(db.collection("appointments").stream())
    print(f"Total turnos: {len(all_appointments)}")

    updated = 0
    skipped_no_donor = 0
    skipped_already_set = 0

    for snap in all_appointments:
        appt = snap.to_dict() or {}
        donor_embed = appt.get("donor") or {}

        if donor_embed.get("blood_group"):
            skipped_already_set += 1
            continue

        donor_id = appt.get("donor_id")
        dni = donor_embed.get("dni")

        blood_group = get_donor_blood_group(donor_id, dni)

        if not blood_group:
            skipped_no_donor += 1
            print(f"  [SKIP] {snap.id} — no se encontró donante (donor_id={donor_id}, dni={dni})")
            continue

        db.collection("appointments").document(snap.id).update({
            "donor.blood_group": blood_group
        })
        updated += 1
        print(f"  [OK]   {snap.id} — donor.blood_group = {blood_group}")

    print(f"\nMigración finalizada.")
    print(f"  Actualizados:        {updated}")
    print(f"  Ya tenían blood_group: {skipped_already_set}")
    print(f"  Sin donante encontrado: {skipped_no_donor}")


if __name__ == "__main__":
    run()
