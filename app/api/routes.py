from fastapi import APIRouter

from app.api.endpoints.health import router as health_router
from app.api.endpoints.documents import router as documents_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(documents_router)