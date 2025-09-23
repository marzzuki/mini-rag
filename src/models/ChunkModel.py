import math

from bson.objectid import ObjectId
from pymongo import InsertOne

from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk
from .enums.DataBaseEnum import DataBaseEnum


class ChunkModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = self.db_client[DataBaseEnum.COLLECTION_CHUNK_NAME.value]

    async def create_chunk(self, chunk: DataChunk):
        payload = chunk.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(payload)
        chunk.id = result.inserted_id
        return chunk

    async def get_chunk(self, chunk_id: str):
        record = await self.collection.find_one({"_id": ObjectId(chunk_id)})

        if record is None:
            return None

        return DataChunk(**record)

    async def insert_many_chunks(self, chunks: list, batch_size: int = 100):
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            documents = [
                chunk.model_dump(by_alias=True, exclude_none=True) for chunk in batch
            ]

            await self.collection.insert_many(documents)

        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: str):
        result = await self.collection.delete_many({"chunk_project_id": project_id})
        return result.deleted_count
