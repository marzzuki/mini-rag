import logging
import os
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, Depends, Request, UploadFile, status
from fastapi.responses import JSONResponse

from controllers import FileController
from helpers.config import Settings, get_settings
from models import (
    AssetModel,
    ProjectModel,
    ResponseMessageEnum,
)
from models.db_schemas import Asset
from models.enums import AssetTypeEnum
from tasks.file_processing import task_process_project_files

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

    task = task_process_project_files.delay(
        project_id=project_id,
        chunk_size=chunk_size,
        file_id=process_request.file_id,
        overlap_size=overlap_size,
        is_reset=is_reset,
    )

    return JSONResponse(
        content={
            "message": ResponseMessageEnum.FILE_PROCESS_SUCCESS.value,
            "task_id": task.id,
        },
    )
