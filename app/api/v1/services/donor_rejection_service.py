from datetime import datetime, timezone
import traceback

from app.firebase.firebase_client import db

COLLECTION = "donor_invitations"
DONORS_COLLECTION = "donors"


def create_donor_rejection_service(
    donor_id: str,
    hospital_request_id: str,
    reason: str,
    notes: str | None,
) -> dict:
    """
    Registra que un donante respondió (o no respondió) a una invitación.
    Si reason == 'opt_out', actualiza is_subscribed = False en el documento del donante.
    Devuelve el registro creado junto con el is_subscribed final del donante.
    """
    try:
        print(f"[DONOR_REJECTION_SERVICE] donor_id={donor_id} reason={reason}")

        recorded_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        record = {
            "donor_id": donor_id,
            "hospital_request_id": hospital_request_id,
            "reason": reason,
            "notes": notes,
            "recorded_at": recorded_at,
        }

        db.collection(COLLECTION).add(record)

        # Si el donante no quiere más avisos, dar de baja la suscripción
        if reason == "opt_out":
            db.collection(DONORS_COLLECTION).document(donor_id).update(
                {"is_subscribed": False}
            )
            is_subscribed = False
        else:
            donor_snap = db.collection(DONORS_COLLECTION).document(donor_id).get()
            donor_data = donor_snap.to_dict() or {} if donor_snap.exists else {}
            is_subscribed = donor_data.get("is_subscribed", True)

        return {
            "donor_id": donor_id,
            "hospital_request_id": hospital_request_id,
            "reason": reason,
            "recorded_at": recorded_at,
            "is_subscribed": is_subscribed,
        }

    except Exception:
        print("[DONOR_REJECTION_SERVICE] ERROR en create_donor_rejection_service")
        traceback.print_exc()
        raise
