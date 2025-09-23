from typing import Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from pydantic import field_validator


class Project(BaseModel):
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    project_id: str = Field(..., min_length=1)

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("project_id must be alpohanumeric")
        return value

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )
