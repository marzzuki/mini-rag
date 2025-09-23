import logging
from contextlib import contextmanager
from curses import meta

import aiofiles
from fastapi import APIRouter, Depends, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import FileController, ProcessController
from helpers.config import Settings, get_settings
from models import ProjectModel, ResponseMessageEnum

from .schemas import ProcessRequest

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(prefix="/api/v1/data", tags=["api_v1", "data"])


@data_router.post("/upload/{project_id}")
async def upload_data(
    request: Request,
    project_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
):
    project_model = ProjectModel(db_client=request.app.db_client)
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

    return JSONResponse(
        content={
            "message": ResponseMessageEnum.FILE_UPLOAD_SUCCESS.value,
            "file_id": file_id,
            "project_id": str(project.id),
        }
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(project_id: str, process_request: ProcessRequest):
    file_id = process_request.file_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    is_reset = process_request.is_reset

    process_controller = ProcessController(project_id=project_id)
    file_content = process_controller.get_file_content(file_id=file_id)
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

    return JSONResponse(
        content={
            "file_chunks": jsonable_encoder(file_chunks),
            "message": ResponseMessageEnum.FILE_PROCESS_SUCCESS.value,
        },
    )
