from datetime import datetime
from firebase_admin import auth
from app.firebase.firebase_client import db

COLLECTION = "users"

def create_admin_user_from_onboarding(req: dict, hospital_id: str) -> str:
    admin = req.get("admin", {})

    email = admin.get("email")

    # 1) Auth user (si ya existe, reutilizar)
    try:
        user = auth.get_user_by_email(email)
        uid = user.uid
    except auth.UserNotFoundError:
        user = auth.create_user(email=email)
        uid = user.uid

    # 2) users/{uid}
    now = datetime.utcnow().isoformat()
    user_data = {
        "uid": uid,
        "email": email,
        "firstName": admin.get("firstName"),
        "lastName": admin.get("lastName"),
        "phone": admin.get("phone"),
        "dni": admin.get("dni"),
        "role": "HOSPITAL_ADMIN",
        "hospitalId": hospital_id,
        "createdAt": now,
    }

    db.collection(COLLECTION).document(uid).set(user_data)
    return uid
