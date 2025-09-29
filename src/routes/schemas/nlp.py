from pydantic import BaseModel


class PushRequest(BaseModel):
    is_reset: bool = False


class SearchRequest(BaseModel):
    text: str
    limit: int | None = 10
