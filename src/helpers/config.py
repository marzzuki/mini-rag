from pydantic_settings import BaseSettings, SettingsConfigDict


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

    OPEN_API_KEY: str
    OPEN_API_URL: str
    COHERE_API_KEY: str

    GENERATION_MODEL_ID: str = None
    EMBEDDING_MODEL_ID: str = None
    EMBEDDING_MODEL_SIZE: str = None

    INPUT_DEFAULT_MAX_CHARACTERS: str = None
    GENERATION_DEFAULT_MAX_OUTPUT_TOKENS: str = None
    GENERATION_DEFAULT_TEMPERATURE: str = None

    class Config:
        env_file = ".env"


def get_settings():
    return Settings()
