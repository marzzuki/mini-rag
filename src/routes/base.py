import logging

from fastapi import APIRouter, Depends

from helpers.config import Settings, get_settings
from tasks.mail_service import task_send_reports

logger = logging.getLogger("uvicorn.error")
base_router = APIRouter(prefix="/api/v1", tags=["api_v1"])


@base_router.get("/")
async def welcome(app_settings: Settings = Depends(get_settings)):
    return {
        "APP_NAME": app_settings.APP_NAME,
        "APP_VERSION": app_settings.APP_VERSION,
    }


@base_router.get("/send_reports")
async def send_reports(app_settings: Settings = Depends(get_settings)):
    task = task_send_reports.delay(
        mail_wait_seconds=3,
    )

    return {
        "success": True,
        "message": task.id,
    }
