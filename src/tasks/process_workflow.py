import asyncio
import logging

from celery import chain

from celery_app import celery_app
from tasks.data_indexing import _index_project
from tasks.file_processing import task_process_project_files

logger = logging.getLogger("celery.task")


@celery_app.task(
    bind=True,
    name="tasks.process_workflow.push_after_process_task",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def push_after_process_task(
    self,
    previous_task_results,
):
    project_id = previous_task_results.get("project_id")
    is_reset = previous_task_results.get("is_reset")

    task_results = asyncio.run(_index_project(self, project_id, is_reset))
    return {
        "project_id": project_id,
        "is_reset": is_reset,
        "task_results": task_results,
    }


@celery_app.task(
    bind=True,
    name="tasks.process_workflow.process_and_push_workflow",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
)
def process_and_push_workflow(
    self,
    project_id: int,
    file_id: int,
    chunk_size: int,
    overlap_size: int,
    is_reset: bool,
):
    workflow = chain(
        task_process_project_files.s(
            project_id=project_id,
            file_id=file_id,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
            is_reset=is_reset,
        ),
        push_after_process_task.s(),
    )

    result = workflow.apply_async()

    return {
        "message": "WORKFLOW STARTED",
        "workflow_id": result.id,
        "tasks": [
            "task_process_project_files",
            "push_after_process_task",
        ],
    }
