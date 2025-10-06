import asyncio
import logging
from datetime import datetime

from celery_app import celery_app

logger = logging.getLogger("celery.tasks")


@celery_app.task(bind=True, name="tasks.mail_service.task_send_reports")
def task_send_reports(self, mail_wait_seconds: int):
    return asyncio.run(_send_reports(self, mail_wait_seconds))


async def _send_reports(task_instance, mail_wait_seconds: int):
    started_at = str(datetime.now())
    task_instance.update_state(
        state="PROGRESS",
        meta={
            started_at: started_at,
        },
    )
    for i in range(15):
        logger.info(f"Send email to user: {i}")
        await asyncio.sleep(mail_wait_seconds)

    return {
        "success": True,
        "message": "Sent 15 emails",
    }
