from controllers.BaseController import BaseController

from .providers import QdrantDBProvider
from .VectorDBEnums import VectorDBEnums


class VectorDBProviderFactory:
    def __init__(self, config) -> None:
        self.conifg = config
        self.base_controller = BaseController()

    def create(self, provider: str):
        if provider == VectorDBEnums.QDRANT.value:
            db_path = self.base_controller.get_database_path(
                db_name=self.config.VECTOR_DB_PATH
            )
            return QdrantDBProvider(
                db_path=db_path, distance_method=self.config.VECTOR_DB_DISTANCE_METHOD
            )

        return None
