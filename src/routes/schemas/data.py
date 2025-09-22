from typing import Optional

from pydantic import BaseModel


class ProcessRequest(BaseModel):
    file_id: str
    chunk_size: Optional[int] = 100
    overlap_size: Optional[int] = 20
    is_reset: Optional[bool] = False
