from abc import ABC, abstractmethod


class VectorDBInterface(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def is_collection_exist(self, collection_name: str) -> bool:
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict:
        pass

    @abstractmethod
    def list_all_collections(self) -> list:
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str):
        pass

    @abstractmethod
    def create_collection(
        self, collection_name: str, embedding_size: int, do_reset: bool = False
    ):
        pass

    @abstractmethod
    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list,
        metadata: dict | None = None,
        record_id: str | None = None,
    ) -> bool:
        pass

    @abstractmethod
    def insert_many(
        self,
        collection_name: str,
        texts: list,
        vectors: list,
        metadata: list | None = None,
        record_ids: list | None = None,
        batch_size: int = 50,
    ) -> bool:
        pass

    @abstractmethod
    def search_by_vector(self, collection_name: str, vector: list, limit: int):
        pass
