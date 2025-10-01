import uuid

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .minirag_base import SQLAlchemyBase


class DataChunk(SQLAlchemyBase):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)

    chunk_uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    chunk_text = Column(String, nullable=False)
    chunk_metadata = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    chunk_order = Column(Integer, nullable=False)

    chunk_project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
    )
    chunk_asset_id = Column(
        Integer,
        ForeignKey("assets.id"),
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

    project = relationship("Project", back_populates="chunks")
    asset = relationship("Asset", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunk_project_id", chunk_project_id),
        Index("ix_chunk_assets_id", chunk_asset_id),
    )


class RetrievedDocument(BaseModel):
    text: str
    score: float
