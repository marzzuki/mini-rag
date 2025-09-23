from typing import Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, Field, validator


class Project(BaseModel):
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    project_id: str = Field(..., min_length=1)

    @validator("project_id")
    def validate_project_id(cls, value):
        if not value.isalnum():
            raise ValueError("project_id must be alpohanumeric")
        return value

    class Config:
        arbitrary_types_allowed = True
        allow_population_by_field_name = True
