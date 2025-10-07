import logging

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from controllers import NLPController
from models import ProjectModel
from models.enums import ResponseMessageEnum
from routes.schemas.nlp import PushRequest, SearchRequest
from tasks.data_indexing import task_index_project

logger = logging.getLogger("uvicorn.error")
nlp_router = APIRouter(prefix="/api/v1/nlp", tags=["api_v1", "nlp"])


@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: int, push_request: PushRequest):
    task = task_index_project.delay(
        project_id=project_id, is_reset=push_request.is_reset
    )

    return JSONResponse(
        content={"message": "Task added to queue Successfully", "task_id": task.id},
    )


@nlp_router.get("/index/info/{project_id}")
async def get_index_info(request: Request, project_id: int):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    collection_info = await nlp_controller.get_vector_db_collection_info(
        project=project
    )

    return JSONResponse(
        content={
            "collection_info": collection_info,
            "message": ResponseMessageEnum.VECTORDB_COLLECTION_RETRIEVED_SUCCESS.value,
        },
    )


@nlp_router.get("/index/search/{project_id}")
async def search_index(
    request: Request, project_id: int, search_request: SearchRequest
):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    results = await nlp_controller.search_vector_db_collection(
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


@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: int, search_request: SearchRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    answer, full_prompt, chat_history = await nlp_controller.answer_rag_question(
        project=project, query=search_request.text, limit=search_request.limit
    )

    if not answer:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": ResponseMessageEnum.RAG_SEARCH_ERROR.value,
            },
        )

    return JSONResponse(
        content={
            "message": ResponseMessageEnum.RAG_SEARCH_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        },
    )
