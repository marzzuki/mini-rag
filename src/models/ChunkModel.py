from sqlalchemy import delete, func
from sqlalchemy.future import select

from .BaseDataModel import BaseDataModel
from .db_schemas import DataChunk


class ChunkModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client)
        self.collection = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance

    async def create_chunk(self, chunk: DataChunk):
        async with self.db_client() as session:
            async with session.begin():
                session.add(chunk)
            await session.commit()
            await session.refresh(chunk)
        return chunk

    async def get_chunk(self, chunk_id: int):
        async with self.db_client() as session:
            result = await session.execute(
                select(DataChunk).where(DataChunk.id == chunk_id)
            )
            chunk = result.scalar_one_or_none()
        return chunk

    async def insert_many_chunks(self, chunks: list, batch_size: int = 100):
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i : i + batch_size]
                    for chunk in batch:
                        if chunk.chunk_metadata is None:
                            chunk.chunk_metadata = {}
                    session.add_all(batch)
            await session.commit()
        return len(chunks)

    async def delete_chunks_by_project_id(self, project_id: int):
        async with self.db_client() as session:
            stmt = delete(DataChunk).where(DataChunk.chunk_project_id == project_id)
            result = await session.execute(stmt)
            await session.commit()
        return result.rowcount

    async def get_all_project_chunks(
        self, project_id: int, page_no: int = 1, page_size: int = 50
    ):
        async with self.db_client() as session:
            stmt = (
                select(DataChunk)
                .where(DataChunk.chunk_project_id == project_id)
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
        return records

    async def get_total_chunks_count(self, project_id: int):
        async with self.db_client() as session:
            count_sql = select(func.count(DataChunk.id)).where(
                DataChunk.chunk_project_id == project_id
            )

            records_count = await session.execute(count_sql)
            total_count = records_count.scalar()
        return total_count
