from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .minirag_base import SQLAlchemyBase


class CeleryTask(SQLAlchemyBase):
    __tablename__ = "celery_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        UUID(as_uuid=True),
        nullable=True,
    )
    task_name = Column(String(255), nullable=False)
    task_args_hash = Column(String(64), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    task_args = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_task_name_args_hash", task_name, task_args_hash, task_id, unique=True),
        Index("ix_task_execution_status", status),
        Index("ix_task_execution_created_at", created_at),
        Index("ix_celery_task_id", task_id),
    )
