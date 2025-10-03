import json
import time
import asyncio

from models.db_schemas import DataChunk, Project
from stores.llm.LLMEnums import DocumentTypeEnum

from .BaseController import BaseController


class NLPController(BaseController):
    def __init__(
        self, vectordb_client, generation_client, embedding_client, template_parser
    ):
        super().__init__()

        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser

    def create_collection_name(self, project_id: str):
        return f"collection_{self.vectordb_client.default_vector_size}_{project_id}".strip()

    def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)

    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)
        collection_info = await self.vectordb_client.get_collection_info(
            collection_name=collection_name
        )

        return json.loads(json.dumps(collection_info, default=lambda x: x.__dict__))

    async def index_into_vector_db(
        self,
        project: Project,
        chunks: list[DataChunk],
        chunks_ids: list[int],
        is_reset: bool = False,
    ):
        collection_name = self.create_collection_name(project_id=project.project_id)
        texts = [c.chunk_text for c in chunks]
        metadatas = [c.chunk_metadata for c in chunks]

        vectors = self.embedding_client.embed_text(
            text=texts,
            document_type=DocumentTypeEnum.DOCUMENT.value,
        )

        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            is_reset=is_reset,
            embedding_size=self.embedding_client.embedding_size,
        )
        _ = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadatas,
            vectors=vectors,
            record_ids=chunks_ids,
        )

        return True

    async def search_vector_db_collection(
        self, project: Project, text: str, limit: int = 10
    ):
        collection_name = self.create_collection_name(project_id=project.project_id)

        vectors = self.embedding_client.embed_text(
            text=text, document_type=DocumentTypeEnum.QUERY.value
        )

        if not vectors:
            return False

        query_vector = None
        if isinstance(vectors, list) and len(vectors) > 0:
            query_vector = vectors[0]
        else:
            return False

        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name, vector=query_vector, limit=limit
        )

        if not results:
            return False

        return json.loads(json.dumps(results, default=lambda x: x.__dict__))

    async def answer_rag_question(self, project: Project, query: str, limit: int = 10):
        retrieved_documents = await self.search_vector_db_collection(
            project=project, text=query, limit=limit
        )

        if not retrieved_documents:
            return None

        system_prompt = self.template_parser.get("rag", "system_prompt")

        documents_prompts = "\n".join(
            [
                self.template_parser.get(
                    "rag",
                    "document_prompt",
                    {
                        "doc_num": idx + 1,
                        "chunk_text": self.generation_client.process_text(
                            doc.get("text", "")
                        ),
                    },
                )
                for idx, doc in enumerate(retrieved_documents)
            ]
        )

        footer_prompts = self.template_parser.get(
            "rag", "footer_prompt", {"query": query}
        )

        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]

        full_prompt = "\n\n".join(
            [
                documents_prompts,
                footer_prompts,
            ]
        )

        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )

        return answer, full_prompt, chat_history
