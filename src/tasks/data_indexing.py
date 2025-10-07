import asyncio
import logging

from tqdm.auto import tqdm

from celery_app import celery_app, get_startup_setup
from controllers import NLPController
from models import (
    ChunkModel,
    ProjectModel,
    ResponseMessageEnum,
)

logger = logging.getLogger("celery.task")


@celery_app.task(
    bind=True,
    name="tasks.data_indexing.task_index_project",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def task_index_project(self, project_id, is_reset: bool):
    return asyncio.run(_index_project(self, project_id=project_id, is_reset=is_reset))


async def _index_project(task_instance, project_id, is_reset: bool):
    db_engine = vectordb_client = None
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

        logger.warning("SETUP UTILS WERE LOADED _INDEX_PROJECT")

        project_model = await ProjectModel.create_instance(db_client=db_client)
        project = await project_model.get_project_or_create_one(project_id=project_id)
        chunk_model = await ChunkModel.create_instance(db_client=db_client)

        if not project:
            task_instance.update_state(
                state="FAILURE",
                meta={"signal": ResponseMessageEnum.PROJECT_NOT_FOUND_ERROR.value},
            )
            raise Exception(f"No project found for {project_id}")

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        has_records = True
        page_no = 1

        inserted_items_count = 0
        idx = 0

        collection_name = nlp_controller.create_collection_name(
            project_id=project.project_id
        )

        _ = await vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=embedding_client.embedding_size,
            is_reset=is_reset,
        )

        total_chunks_count = await chunk_model.get_total_chunks_count(
            project_id=project.id
        )
        pbar = tqdm(total=total_chunks_count, desc="Vector Indexing", position=0)

        while has_records:
            page_chunks = await chunk_model.get_all_project_chunks(
                project_id=project.id, page_no=page_no
            )

            if not len(page_chunks):
                has_records = False
                break

            chunks_ids = [c.id for c in page_chunks]
            idx += len(page_chunks)
            page_no += 1

            is_inserted = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=page_chunks,
                chunks_ids=chunks_ids,
            )

            if not is_inserted:
                task_instance.update_state(
                    state="FAILURE",
                    meta={
                        "signal": ResponseMessageEnum.INSERT_INTO_VECTORDB_ERROR.value
                    },
                )
                raise Exception(f"insert to vectordb failed {project_id}")

            pbar.update(len(page_chunks))
            inserted_items_count += len(page_chunks)

        task_instance.update_state(
            state="SUCCESS",
            meta={"message": ResponseMessageEnum.INSERT_INTO_VECTORDB_SUCCESS.value},
        )

        return (
            {
                "message": ResponseMessageEnum.INSERT_INTO_VECTORDB_SUCCESS.value,
                "inserted_items_count": inserted_items_count,
            },
        )
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        task_instance.update_state(
            state="FAILURE",
            meta={
                "exc_type": type(e).__name__,
                "exc_message": str(e),
                "message": ResponseMessageEnum.INSERT_INTO_VECTORDB_ERROR.value,
            },
        )
        raise
    finally:
        try:
            # Ensure db_engine is not None and has a dispose method
            if db_engine is not None and hasattr(db_engine, "dispose"):
                await db_engine.dispose()

            # Ensure vectordb_client is not None and has a disconnect method
            if vectordb_client is not None and hasattr(vectordb_client, "disconnect"):
                vectordb_client.disconnect()
        except Exception as e:
            logger.error(f"Task failed while cleaning: {str(e)}")
