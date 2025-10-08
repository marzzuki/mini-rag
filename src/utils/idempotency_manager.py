import datetime
import hashlib
import json

from sqlalchemy import select

from models.db_schemas.minirag.schemas.celery_task import CeleryTask


class IdempotencyManager:
    def __init__(self, db_client, db_engine):
        self.db_client = db_client
        self.db_engine = db_engine

    def create_hash(self, task_name: str, task_args: dict):
        combined_data = {
            **task_args,
            "task_name": task_name,
        }
        json_string = json.dumps(combined_data, sort_keys=True, default=str)
        return hashlib.sha256(json_string.encode()).hexdigest()

    async def create_task_record(
        self,
        task_name: str,
        task_args: dict,
        celery_task_id: str | None = None,
    ) -> CeleryTask:
        args_hash = self.create_hash(task_name, task_args)

        task_record = CeleryTask(
            task_id=celery_task_id,
            task_args_hash=args_hash,
            task_name=task_name,
            task_args=task_args,
            status="PENDING",
            started_at=None,
        )

        session = self.db_client()
        try:
            session.add(task_record)
            await session.commit()
            await session.refresh(task_record)
            return task_record
        finally:
            await session.close()

    async def update_task_status(
        self, task_id: int, status: str, result: dict = None, celery_task_id: str | None = None
    ):
        """Update task status and result."""
        session = self.db_client()
        try:
            task_record = await session.get(CeleryTask, task_id)
            if task_record:
                task_record.status = status
                if result:
                    task_record.result = result
                if celery_task_id:
                    task_record.task_id = celery_task_id
                if status == "STARTED":
                    task_record.started_at = datetime.datetime.now(datetime.UTC)
                if status in ["SUCCESS", "FAILURE"]:
                    task_record.completed_at = datetime.datetime.now(datetime.UTC)
                await session.commit()
        finally:
            await session.close()

    async def get_existing_task(
        self, task_name: str, task_args: dict, celery_task_id: str
    ) -> CeleryTask:
        args_hash = self.create_hash(task_name, task_args)

        session = self.db_client()
        try:
            stmt = select(CeleryTask).where(
                CeleryTask.task_name == task_name,
                CeleryTask.task_args_hash == args_hash,
                CeleryTask.task_id == celery_task_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
        finally:
            await session.close()

    async def should_execute_task(
        self,
        task_name: str,
        task_args: dict,
        celery_task_id: str,
        task_time_limit: int = 600,
    ) -> tuple[bool, CeleryTask | None]:
        """
        Check if task should be executed or return existing result.
        Args:
            task_time_limit: Time limit in seconds after which a stuck task can be re-executed
        Returns (should_execute, existing_task_or_none)
        """
        existing_task = await self.get_existing_task(
            task_name, task_args, celery_task_id
        )

        if not existing_task:
            return True, None

        # Don't execute if task is already completed successfully
        if existing_task.status == "SUCCESS":
            return False, existing_task

        # Check if task is stuck (running longer than time limit + 60 seconds)
        if existing_task.status in ["PENDING", "STARTED", "RETRY"]:
            if existing_task.started_at:
                time_elapsed = (
                    datetime.datetime.now(datetime.UTC) - existing_task.started_at
                ).total_seconds()
                time_gap = 60  # 60 seconds grace period
                if time_elapsed > (task_time_limit + time_gap):
                    return True, existing_task  # Task is stuck, allow re-execution
            return False, existing_task  # Task is still running within time limit

        # Re-execute if previous task failed
        return True, existing_task
