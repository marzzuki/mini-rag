import asyncio
import logging
from datetime import datetime, timezone

from celery_app import celery_app, get_startup_setup
from controllers import NLPController, ProcessController
from models import (
    AssetModel,
    ChunkModel,
    ProjectModel,
    ResponseMessageEnum,
)
from models.db_schemas import DataChunk
from models.enums import AssetTypeEnum

logger = logging.getLogger("celery.task")


@celery_app.task(
    bind=True,
    name="tasks.file_processing.process_project_files",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def task_process_project_files(
    self,
    project_id: int,
    file_id: int,
    chunk_size: int,
    overlap_size: int,
    is_reset: bool,
):
    asyncio.run(
        _process_project_files(
            self,
            project_id=project_id,
            file_id=file_id,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
            is_reset=is_reset,
        )
    )


async def _process_project_files(
    task_instance,
    project_id: int,
    file_id: int,
    chunk_size: int,
    overlap_size: int,
    is_reset: bool,
):
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

        project_model = await ProjectModel.create_instance(db_client=db_client)
        project = await project_model.get_project_or_create_one(project_id=project_id)

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        chunk_model = await ChunkModel.create_instance(db_client=db_client)

        process_controller = ProcessController(project_id=project_id)
        asset_model = await AssetModel.create_instance(db_client=db_client)

        file_id = file_id
        project_file_ids = {}

        if file_id:
            asset_record = await asset_model.get_asset_record(
                asset_project_id=project.id, asset_name=file_id
            )
            if asset_record is None:
                task_instance.update_state(
                    state="FAILURE",
                    meta={
                        "exc_type": "ValueError",
                        "exc_message": ResponseMessageEnum.FILE_ID_ERROR.value,
                        "message": ResponseMessageEnum.FILE_ID_ERROR.value,
                    },
                )

                raise Exception(f"No Asset Record Found for file_id: {file_id}")

            project_file_ids = {asset_record.id: asset_record.asset_name}
        else:
            project_files = await asset_model.get_all_project_assets(
                project.id, AssetTypeEnum.FILE.value
            )
            project_file_ids = {
                record.id: record.asset_name for record in project_files
            }

        if not project_file_ids:
            task_instance.update_state(
                state="FAILURE",
                meta={
                    "exc_type": "ValueError",
                    "exc_message": ResponseMessageEnum.NO_FILES_ERROR.value,
                    "message": ResponseMessageEnum.NO_FILES_ERROR.value,
                },
            )
            raise Exception(
                f"No Project file ids Found for project_file_ids: {project_file_ids}"
            )

        total_chunks = 0
        processed_files = 0

        if is_reset:
            collection_name = nlp_controller.create_collection_name(
                project_id=project.project_id
            )
            _ = await vectordb_client.delete_collection(collection_name)

            await chunk_model.delete_chunks_by_project_id(project_id=project.id)

        for asset_id, file_id in project_file_ids.items():
            file_content = process_controller.get_file_content(file_id=file_id)

            if file_content is None:
                logger.error(f"Error while processing file: {file_id}")

            file_chunks = process_controller.process_file_content(
                file_content=file_content,
                chunk_size=chunk_size,
                overlap_size=overlap_size,
            )

            if file_chunks is None or len(file_chunks) == 0:
                logger.error(f"No chunks for file_id: {file_id}")
                pass

            chunk_timestamp = datetime.now(timezone.utc)

            file_chunks_records = [
                DataChunk(
                    chunk_text=chunk.page_content,
                    chunk_metadata=chunk.metadata or {},
                    chunk_order=i + 1,
                    chunk_project_id=project.id,
                    chunk_asset_id=asset_id,
                    updated_at=chunk_timestamp,
                )
                for i, chunk in enumerate(file_chunks)
            ]

            total_chunks += await chunk_model.insert_many_chunks(
                chunks=file_chunks_records
            )
            processed_files += 1

        logger.info(
            f"Task process_project_files for project_id: {project_id} completed successfully. Total chunks: {total_chunks}, Processed files: {processed_files}"
        )
        task_instance.update_state(
            state="SUCCESS",
            meta={
                "message": ResponseMessageEnum.FILE_PROCESS_SUCCESS.value,
            },
        )

        return {
            "total_chunks": total_chunks,
            "processed_files": processed_files,
            "message": ResponseMessageEnum.FILE_PROCESS_SUCCESS.value,
        }

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        task_instance.update_state(
            state="FAILURE",
            meta={
                "exc_type": type(e).__name__,
                "exc_message": str(e),
                "message": ResponseMessageEnum.FILE_PROCESS_FAILED.value,
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
