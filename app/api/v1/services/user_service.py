from datetime import datetime
from firebase_admin import auth
from app.firebase.firebase_client import db

COLLECTION = "users"

def create_admin_user_from_onboarding(req: dict, hospital_id: str) -> str:
    admin = req.get("admin", {})

    email = admin.get("email")
    first_name = admin.get("firstName")
    last_name = admin.get("lastName")
    phone = admin.get("phone")

    if not email:
        raise Exception("Admin email missing in onboarding request")

    # 1) Auth user
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
        "firstName": first_name,
        "lastName": last_name,
        "phone": phone,
        "role": "HOSPITAL_ADMIN",
        "hospitalId": hospital_id,
        "createdAt": now,
    }

    db.collection(COLLECTION).document(uid).set(user_data)

    return uid
