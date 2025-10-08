import asyncio
import logging

from celery_app import celery_app, get_startup_setup
from utils.idempotency_manager import IdempotencyManager

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="tasks.maintenance.clean_celery_executions_table",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def clean_celery_executions_table(self):
    return asyncio.run(_clean_celery_executions_table(self))


async def _clean_celery_executions_table(task_instance):
    db_engine, vectordb_client = None, None

    try:
        (
            db_engine,
            db_client,
            llm_provider_factory,
            vectordb_provider_factory,
            generation_client,
            embedding_client,
            vectordb_client,
            template_parser,
        ) = await get_startup_setup()

        # Create idempotency manager
        idempotency_manager = IdempotencyManager(db_client, db_engine)

        logger.warning("cleaning !!!")
        _ = await idempotency_manager.cleanup_old_tasks(5)

        return True

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise
    finally:
        try:
            dispose_method = getattr(db_engine, "dispose", None)
            if db_engine is not None and callable(dispose_method):
                await dispose_method()

            disconnect_method = getattr(vectordb_client, "disconnect", None)
            if vectordb_client is not None and callable(disconnect_method):
                disconnect_method()
        except Exception as e:
            logger.error(f"Task failed while cleaning: {str(e)}")
