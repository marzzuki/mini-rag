from datetime import datetime
from typing import Optional

from bson.objectid import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class Asset(BaseModel):
    id: Optional[ObjectId] = Field(default=None, alias="_id")
    asset_project_id: ObjectId
    asset_type: str = Field(..., min_length=1)
    asset_name: str = Field(..., min_length=1)
    asset_size: int = Field(ge=0, default=None)
    asset_config: dict = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def get_indexes(cls):
        return [
            {
                "key": [("asset_project_id", 1)],
                "name": "asset_project_id_index_1",
                "unique": False,
            },
            {
                "key": [("asset_project_id", 1), ("asset_name", 1)],
                "name": "asset_project_id_name_index_1",
                "unique": True,
            },
        ]

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )
