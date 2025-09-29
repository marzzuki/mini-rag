from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    FILE_ALLOWED_EXTENSIONS: list[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int
    MONGODB_URL: str
    MONGODB_DATABASE: str
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    OPENAI_API_KEY: str
    OPENAI_API_URL: str
    COHERE_API_KEY: str

    GENERATION_MODEL_ID: str | None = None
    EMBEDDING_MODEL_ID: str | None = None
    EMBEDDING_MODEL_SIZE: str | None = None

    INPUT_DEFAULT_MAX_CHARACTERS: int | None = None
    GENERATION_DEFAULT_MAX_OUTPUT_TOKENS: int | None = None
    GENERATION_DEFAULT_TEMPERATURE: float | None = None

    VECTOR_DB_BACKEND: str
    VECTOR_DB_PATH: str
    VECTOR_DB_DISTANCE_METHOD: str | None = None

    class Config:
        env_file = ".env"


def get_settings():
    return Settings()
