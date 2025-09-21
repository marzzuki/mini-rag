from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import JSONResponse
from helpers.config import get_settings, Settings
from controllers import FileController, ProjectController
from models import ResponseMessage
import aiofiles
import logging

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(prefix="/api/v1/data", tags=["api_v1", "data"])


@data_router.post("/upload/{project_id}")
async def upload(
    project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)
):
    file_controller = FileController()
    is_valid, message = file_controller.validate_uploaded_file(file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content={"message": message}
        )

    file_path = file_controller.generate_unique_filename(
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
            content={"message": ResponseMessage.FILE_UPLOAD_FAILED},
        )

    return JSONResponse(content={"message": ResponseMessage.FILE_UPLOAD_SUCCESS.value})
