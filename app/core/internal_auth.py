import os
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN")


def check_internal_token(x_internal_token: str | None):
    print("=== VITFLOW INTERNAL AUTH ===")
    print("ENV INTERNAL_TOKEN =", INTERNAL_TOKEN)
    print("HEADER x_internal_token =", x_internal_token)
    print("=============================")

    if not INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="INTERNAL_TOKEN no configurado",
        )

    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized internal token",
        )