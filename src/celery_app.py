from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory

settings = get_settings()


async def get_startup_setup():
    settings = get_settings()

    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
    db_engine = create_async_engine(postgres_conn)
    db_client = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(settings, db_client=db_client)

    generation_client = llm_provider_factory.create(
        provider=settings.GENERATION_BACKEND
    )

    vectordb_client = vectordb_provider_factory.create(
        provider=settings.VECTOR_DB_BACKEND
    )
    await vectordb_client.connect()
    generation_client.set_generation_model(model_id=settings.GENERATION_MODEL_ID)

    embedding_client = llm_provider_factory.create(provider=settings.EMBEDDING_BACKEND)
    embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE,
    )

    template_parser = TemplateParser(
        language=settings.PRIMARY_LANG, default_language=settings.DEFAULT_LANG
    )

    return (
        db_engine,
        db_client,
        llm_provider_factory,
        vectordb_provider_factory,
        generation_client,
        embedding_client,
        vectordb_client,
        template_parser,
    )


# Create Celery application instance
celery_app = Celery(
    "minirag",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.file_processing",
        "tasks.data_indexing",
        "tasks.process_workflow",
        "tasks.maintenance",
    ],
)

# Configure Celery ith essential settings
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=[settings.CELERY_TASK_SERIALIZER],
    # Task safety - Late acknowledgment prevents task loss on worker crash
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    # Time limits - Prevent hanging tasks
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    # Result backend - Store results for status tracking
    task_ignore_result=False,
    result_expires=3600,
    # Worker settings
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    # Connection settings for better reliability
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_routes={
        "tasks.file_processing.process_project_files": {"queue": "file_processing"},
        "tasks.data_indexing.task_index_project": {"queue": "index_project"},
        "tasks.process_workflow.process_and_push_workflow": {
            "queue": "process_push_workflow"
        },
        "tasks.maintenance.clean_celery_executions_table": {"queue": "default"},
    },
    beat_schedule={
        "cleanup-old-task-records": {
            "task": "tasks.maintenance.clean_celery_executions_table",
            "schedule": 84600,
            "args": (),
        }
    },
)

celery_app.conf.task_default_queue = "default"
