import logging
import os
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, Depends, Request, UploadFile, status
from fastapi.responses import JSONResponse

from controllers import FileController, NLPController, ProcessController
from helpers.config import Settings, get_settings
from models import (
    AssetModel,
    ChunkModel,
    ProjectModel,
    ResponseMessageEnum,
)
from models.db_schemas import Asset, DataChunk
from models.enums import AssetTypeEnum

from .schemas import ProcessRequest

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(prefix="/api/v1/data", tags=["api_v1", "data"])


@data_router.post("/upload/{project_id}")
async def upload_data(
    request: Request,
    project_id: int,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    file_controller = FileController()
    is_valid, message = file_controller.validate_uploaded_file(file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"message": message}
        )
    file_path, file_id = file_controller.generate_unique_filename(
        orig_file_name=file.filename, project_id=project_id
    )

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:
        logger.error(f"Error while uploading file: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnum.FILE_UPLOAD_FAILED},
        )

    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_timestamp = datetime.now(timezone.utc)

    asset_resource = Asset(
        asset_project_id=project.id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_id,
        asset_size=os.path.getsize(file_path),
        asset_config={
            "original_filename": file.filename,
            "content_type": file.content_type,
        },
        updated_at=asset_timestamp,
    )
    asset_record = await asset_model.create_asset(asset=asset_resource)
    return JSONResponse(
        content={
            "message": ResponseMessageEnum.FILE_UPLOAD_SUCCESS.value,
            "file_id": file_id,
            "asset_id": str(asset_record.id),
        }
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(
    request: Request, project_id: int, process_request: ProcessRequest
):
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    is_reset = process_request.is_reset

    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    process_controller = ProcessController(project_id=project_id)
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)

    file_id = process_request.file_id
    project_file_ids = {}

    if file_id:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.id, asset_name=process_request.file_id
        )
        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": ResponseMessageEnum.FILE_ID_ERROR.value},
            )
        project_file_ids = {asset_record.id: asset_record.asset_name}
    else:
        project_files = await asset_model.get_all_project_assets(
            project.id, AssetTypeEnum.FILE.value
        )
        project_file_ids = {record.id: record.asset_name for record in project_files}

    if not project_file_ids:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnum.NO_FILES_ERROR.value},
        )

    total_chunks = 0
    processed_files = 0

    if is_reset:
        collection_name = nlp_controller.create_collection_name(
            project_id=project.project_id
        )
        _ = await request.app.vectordb_client.delete_collection(collection_name)

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
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": ResponseMessageEnum.FILE_PROCESS_FAILED.value},
            )

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

        total_chunks += await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        processed_files += 1

    return JSONResponse(
        content={
            "total_chunks": total_chunks,
            "processed_files": processed_files,
            "message": ResponseMessageEnum.FILE_PROCESS_SUCCESS.value,
        },
    )
