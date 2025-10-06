import logging

from fastapi import APIRouter, Depends

from helpers.config import Settings, get_settings

logger = logging.getLogger("uvicorn.error")
base_router = APIRouter(prefix="/api/v1", tags=["api_v1"])


@base_router.get("/")
async def welcome(app_settings: Settings = Depends(get_settings)):
    return {
        "APP_NAME": app_settings.APP_NAME,
        "APP_VERSION": app_settings.APP_VERSION,
    }
