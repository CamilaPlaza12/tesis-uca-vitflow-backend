import re

from firebase_admin import auth as firebase_auth
from fastapi import HTTPException, status

from app.schemas.auth_schema import RegisterRequest
from app.firebase.firebase_client import db


def validate_email(email: str) -> None:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email no tiene un formato válido.",
        )


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres.",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe incluir al menos una letra mayúscula.",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe incluir al menos una letra minúscula.",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe incluir al menos un número.",
        )
    if not re.search(r"[^\w\s]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe incluir al menos un carácter especial.",
        )
    if re.search(r"\s", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña no puede contener espacios.",
        )


async def create_firebase_user(data: RegisterRequest):
    validate_email(data.email)
    validate_password(data.password)

    try:
        user_record = firebase_auth.create_user(
            email=data.email,
            password=data.password,
            display_name=data.full_name,
            phone_number=data.phone_number,
        )
        return user_record
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear el usuario en Firebase.",
        )


async def create_user_profile(uid: str, data: RegisterRequest):
    profile_data = {
        "uid": uid,
        "email": data.email,
        "full_name": data.full_name,
        "phone_number": data.phone_number,
        "address": data.address.model_dump(),
    }
    db.collection("users").document(uid).set(profile_data)


async def get_user_profile(uid: str):
    doc = db.collection("users").document(uid).get()
    if not doc.exists:
        return None
    return doc.to_dict()
