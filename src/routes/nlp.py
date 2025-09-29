import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from controllers import NLPController
from models import ChunkModel, ProjectModel
from models.enums import ResponseMessageEnum
from routes.schemas.nlp import PushRequest, SearchRequest

logger = logging.getLogger("uvicorn.error")
nlp_router = APIRouter(prefix="/api/v1/nlp", tags=["api_v1", "nlp"])


@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)

    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnum.PROJECT_NOT_FOUND_ERROR.value},
        )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

    has_records = True
    page_no = 1

    inserted_items_count = 0
    idx = 0

    while has_records:
        page_chunks = await chunk_model.get_all_project_chunks(
            project_id=project.id, page_no=page_no
        )

        if not len(page_chunks):
            has_records = False
            break

        chunks_ids = list(range(idx, idx + len(page_chunks)))
        idx += len(page_chunks)
        page_no += 1

        is_inserted = nlp_controller.index_into_vector_db(
            project=project,
            chunks=page_chunks,
            chunks_ids=chunks_ids,
            do_reset=push_request.is_reset,
        )

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": ResponseMessageEnum.INSERT_INTO_VECTORDB_ERROR.value
                },
            )

        inserted_items_count += len(page_chunks)

    return JSONResponse(
        content={
            "message": ResponseMessageEnum.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        },
    )


@nlp_router.get("/index/info/{project_id}")
async def get_index_info(request: Request, project_id: str):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

    collection_info = nlp_controller.get_vector_db_collection_info(project=project)

    return JSONResponse(
        content={
            "collection_info": collection_info,
            "message": ResponseMessageEnum.VECTORDB_COLLECTION_RETRIEVED_SUCCESS.value,
        },
    )


@nlp_router.get("/index/search/{project_id}")
async def search_index(
    request: Request, project_id: str, search_request: SearchRequest
):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
    )

    results = nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )

    if not results:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseMessageEnum.VECTORDB_SEARCH_ERROR.value},
        )

    return JSONResponse(
        content={
            "message": ResponseMessageEnum.VECTORDB_SEARCH_SUCCESS.value,
            "results": results,
        },
    )
