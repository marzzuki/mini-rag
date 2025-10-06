import asyncio
import json
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import text as sql_text

from models.db_schemas import RetrievedDocument

from ..VectorDBEnums import (
    DistanceMethodEnums,
    PgVectorDistanceMethodEnums,
    PgVectorIndexTypeEnums,
    PgVectorTableSchemaEnums,
)
from ..VectorDBInterface import VectorDBInterface


class PGVectorProvider(VectorDBInterface):
    def __init__(
        self,
        db_client,
        distance_method: str = None,
        default_vector_size: int = 786,
        index_threshold: int = 100,
    ):
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold

        if distance_method == DistanceMethodEnums.COSINE.value:
            self.distance_method = PgVectorDistanceMethodEnums.COSINE.value
        elif distance_method == DistanceMethodEnums.DOT.value:
            self.distance_method = PgVectorDistanceMethodEnums.DOT.value

        self.pgvector_table_prefix = PgVectorTableSchemaEnums._PREFIX.value
        self.default_index_name = (
            lambda collection_name: f"{collection_name}_vector_idx"
        )

        self.logger = logging.getLogger("uvicorn")

    async def connect(self):
        async with self.db_client() as session:
            try:
                await session.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                error_msg = str(exc).lower()
                if (
                    "pg_extension_name_index" in error_msg
                    or "duplicate key value" in error_msg
                ):
                    self.logger.info(
                        "pgvector extension already installed; skipping creation"
                    )
                else:
                    raise

    def disconnect(self):
        pass

    async def is_collection_exist(self, collection_name: str) -> bool:
        record = None

        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(
                    "SELECT * FROM pg_tables WHERE tablename = :collection_name"
                )
                results = await session.execute(
                    list_tbl, {"collection_name": collection_name}
                )
                record = results.scalar_one_or_none()

        return record

    async def list_all_collections(self) -> list:
        records = []

        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(
                    "SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix"
                )
                results = await session.execute(
                    list_tbl, {"prefix": self.pgvector_table_prefix}
                )
                records = results.scalars().all()

        return records

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text(
                    """
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                    FROM pg_tables
                    WHERE tablename = :collection_name
                """
                )

                # Properly quote the table name for PostgreSQL
                def quote_identifier(identifier):
                    return '"' + identifier.replace('"', '""') + '"'

                table_name_quoted = quote_identifier(collection_name)
                count_sql = sql_text(f"SELECT COUNT(*) FROM {table_name_quoted}")

                table_info = await session.execute(
                    table_info_sql, {"collection_name": collection_name}
                )
                record_count_result = await session.execute(count_sql)
                record_count = (
                    record_count_result.scalar() if record_count_result else None
                )

                table_data = table_info.fetchone()
                if not table_data:
                    return None

                return {
                    "table_data": dict(table_data._mapping),
                    "record_count": record_count,
                }

    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection: {collection_name}")

                def quote_identifier(identifier):
                    return '"' + identifier.replace('"', '""') + '"'

                table_name_quoted = quote_identifier(collection_name)
                delete_sql = sql_text(f"DROP TABLE IF EXISTS {table_name_quoted}")
                await session.execute(delete_sql)
                await session.commit()

        return True

    async def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        is_reset: bool = False,
    ):
        if is_reset:
            _ = await self.delete_collection(collection_name)

        if not await self.is_collection_exist(collection_name):
            async with self.db_client() as session:
                async with session.begin():

                    def quote_identifier(identifier):
                        return '"' + identifier.replace('"', '""') + '"'

                    table_name_quoted = quote_identifier(collection_name)
                    create_sql = sql_text(
                        f"CREATE TABLE {table_name_quoted} ("
                        f"{PgVectorTableSchemaEnums.ID.value} bigserial PRIMARY KEY,"
                        f"{PgVectorTableSchemaEnums.TEXT.value} text,"
                        f"{PgVectorTableSchemaEnums.VECTOR.value} vector({embedding_size}),"
                        f"{PgVectorTableSchemaEnums.METADATA.value} jsonb DEFAULT '{{}}',"
                        f"{PgVectorTableSchemaEnums.CHUNK_ID.value} integer,"
                        f"FOREIGN KEY ({PgVectorTableSchemaEnums.CHUNK_ID.value}) REFERENCES chunks(id)"
                        ")"
                    )
                    await session.execute(create_sql)
                    await session.commit()
            return True
        return False

    async def is_index_existed(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                check_index_sql = sql_text(
                    """
                                    SELECT 1
                                    FROM pg_indexes
                                    WHERE tablename = :collection_name
                                    AND indexname = :index_name
                                    """
                )
                results = await session.execute(
                    check_index_sql,
                    {"collection_name": collection_name, "index_name": index_name},
                )

                return bool(results.scalar_one_or_none())

    async def create_vector_index(
        self,
        collection_name: str,
        index_type: str = PgVectorIndexTypeEnums.HNSW.value,
    ):
        is_index_exists = await self.is_index_existed(collection_name=collection_name)
        if is_index_exists:
            return False

        async with self.db_client() as session:
            async with session.begin():

                def quote_identifier(identifier):
                    return '"' + identifier.replace('"', '""') + '"'

                table_name_quoted = quote_identifier(collection_name)
                count_sql = sql_text(f"SELECT COUNT(*) FROM {table_name_quoted}")
                result = await session.execute(count_sql)
                records_count = result.scalar_one()

                if records_count < self.index_threshold:
                    return False

                self.logger.info(
                    f"START: Creating vector index for collection: {collection_name}"
                )

                # Add a short sleep for rate limiting
                await asyncio.sleep(1)

                index_name = self.default_index_name(collection_name)

                def quote_identifier(identifier):
                    return '"' + identifier.replace('"', '""') + '"'

                index_name_quoted = quote_identifier(index_name)
                collection_name_quoted = quote_identifier(collection_name)
                create_idx_sql = sql_text(
                    f"CREATE INDEX {index_name_quoted} ON {collection_name_quoted} "
                    f"USING {index_type} ({PgVectorTableSchemaEnums.VECTOR.value} {self.distance_method})"
                )

                await session.execute(create_idx_sql)

                self.logger.info(
                    f"END: Created vector index for collection: {collection_name}"
                )

    async def reset_vector_index(
        self,
        collection_name: str,
        index_type: str = PgVectorIndexTypeEnums.HNSW.value,
    ):
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_sql = sql_text("DROP INDEX IF EXISTS :index_name")
                await session.execute(
                    drop_sql,
                    {
                        "index_name": index_name,
                    },
                )
        return await self.create_vector_index(
            collection_name=collection_name,
            index_type=index_type,
        )

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: dict | None = None,
        record_id: str | None = None,
    ) -> bool:
        if not await self.is_collection_exist(collection_name):
            self.logger.error(
                f"Can't insert new record to non-existed collection: {collection_name}"
            )

            return False

        try:
            if not record_id:
                self.logger.error(
                    f"Can't insert a new record without chunk_id: {collection_name}"
                )
                return False

            async with self.db_client() as session:
                async with session.begin():

                    def quote_identifier(identifier):
                        return '"' + identifier.replace('"', '""') + '"'

                    table_name_quoted = quote_identifier(collection_name)
                    insert_sql = sql_text(
                        f"INSERT INTO {table_name_quoted}"
                        f"({PgVectorTableSchemaEnums.TEXT.value},"
                        f"{PgVectorTableSchemaEnums.VECTOR.value},"
                        f"{PgVectorTableSchemaEnums.METADATA.value},"
                        f"{PgVectorTableSchemaEnums.CHUNK_ID.value})"
                        "VALUES (:text, :vector, :metadata, :chunk_id)"
                    )
                    await session.execute(
                        insert_sql,
                        {
                            "text": text,
                            "vector": "[" + ",".join([str(v) for v in vector]) + "]",
                            "metadata": json.dumps(metadata) if metadata else "{}",
                            "chunk_id": record_id,
                        },
                    )
                    await session.commit()
            await self.create_vector_index(collection_name=collection_name)

        except Exception as e:
            self.logger.error(f"Error while inserting batch: {e}")
            return False

        return True

    async def insert_many(
        self,
        collection_name: str,
        texts: list,
        vectors: list,
        metadata: list | None = None,
        record_ids: list | None = None,
        batch_size: int = 50,
    ) -> bool:
        if not await self.is_collection_exist(collection_name):
            self.logger.error(
                f"Can't insert new record to non-existed collection: {collection_name}"
            )
            return False

        if metadata is None:
            metadata = [None] * len(texts)

        if record_ids is None:
            record_ids = list(range(0, len(texts)))

        if len(vectors) != len(record_ids):
            self.logger.error(f"Invalid data items for collection: {collection_name}")
            return False

        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_end = i + batch_size
                    batch_texts = texts[i:batch_end]
                    batch_vectors = vectors[i:batch_end]
                    batch_metadata = metadata[i:batch_end]
                    batch_record_ids = record_ids[i:batch_end]

                    values = []
                    for _text, _vector, _metadata, _record_id in zip(
                        batch_texts, batch_vectors, batch_metadata, batch_record_ids
                    ):
                        values.append(
                            {
                                "text": _text,
                                "vector": "["
                                + ",".join([str(v) for v in _vector])
                                + "]",
                                "metadata": (
                                    json.dumps(_metadata) if _metadata else "{}"
                                ),
                                "chunk_id": _record_id,
                            }
                        )

                    def quote_identifier(identifier):
                        return '"' + identifier.replace('"', '""') + '"'

                    table_name_quoted = quote_identifier(collection_name)
                    batch_insert_sql = sql_text(
                        f"INSERT INTO {table_name_quoted}"
                        f"({PgVectorTableSchemaEnums.TEXT.value},"
                        f"{PgVectorTableSchemaEnums.VECTOR.value},"
                        f"{PgVectorTableSchemaEnums.METADATA.value},"
                        f"{PgVectorTableSchemaEnums.CHUNK_ID.value})"
                        "VALUES (:text, :vector, :metadata, :chunk_id)"
                    )

                    await session.execute(batch_insert_sql, values)
        await self.create_vector_index(collection_name=collection_name)
        return True

    async def search_by_vector(
        self, collection_name: str, vector: list, limit: int
    ) -> list[RetrievedDocument] | None:
        if not await self.is_collection_exist(collection_name):
            self.logger.error(f"Can't search non-existed collection: {collection_name}")
            return None

        def quote_identifier(identifier):
            return '"' + identifier.replace('"', '""') + '"'

        table_name_quoted = quote_identifier(collection_name)
        # Inline the vector as a pgvector literal
        vector_str = "'[{0}]'::vector".format(",".join(str(v) for v in vector))

        async with self.db_client() as session:
            async with session.begin():
                search_sql = sql_text(
                    f"SELECT {PgVectorTableSchemaEnums.TEXT.value} as text, 1- ({PgVectorTableSchemaEnums.VECTOR.value} <=> {vector_str}) as score FROM {table_name_quoted} ORDER BY score DESC LIMIT :limit"
                )

                result = await session.execute(
                    search_sql,
                    {
                        "limit": limit,
                    },
                )

                records = result.fetchall()

                return [
                    RetrievedDocument(
                        text=record.text,
                        score=record.score,
                    )
                    for record in records
                ]
