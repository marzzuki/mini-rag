from typing import Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator


class Project(BaseModel):
    _id: Optional[ObjectId]
    project_id: str = Field(..., min_length=1)

    @validator("project_id")
    def validate_project_id(cls, value):
        if not value.isalnum():
            raise ValueError("project_id must be alpohanumeric")

    class Config:
        arbitary_types_allowed = True
