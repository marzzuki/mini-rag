import uuid

from sqlalchemy import Column, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .minirag_base import SQLAlchemyBase


class Project(SQLAlchemyBase):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
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

    assets = relationship("Asset", back_populates="project")
    chunks = relationship("DataChunk", back_populates="project")
