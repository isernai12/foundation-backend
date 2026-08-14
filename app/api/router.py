from fastapi import APIRouter
from backend.app.api.v1.router import api_v1_router
from backend.app.core.config import settings

api_router = APIRouter()
api_router.include_router(api_v1_router, prefix=settings.API_V1_STR)
