from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.kb import KBStatus


class KBDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    title: str
    status: KBStatus
    chunk_count: int
    error: str | None
    created_at: datetime


class SearchHit(BaseModel):
    title: str
    section: str | None
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]
