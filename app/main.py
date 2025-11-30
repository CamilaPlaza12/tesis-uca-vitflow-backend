from fastapi import FastAPI

from app.core.config import PROJECT_NAME, API_V1_PREFIX
from app.api.v1.routers import auth_router
from app.firebase import firebase_client

app = FastAPI(title=PROJECT_NAME)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth_router.router, prefix=API_V1_PREFIX)
