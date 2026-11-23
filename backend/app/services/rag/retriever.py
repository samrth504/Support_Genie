"""Semantic search over the knowledge base (pgvector cosine distance).

score = 1 - cosine_distance  ->  1.0 = identical meaning, ~0 = unrelated.
The agent uses the top score to decide confidence and to log knowledge gaps.
"""
from dataclasses import dataclass

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.kb import KBChunk, KBDocument, KBStatus
from app.services.rag import embeddings


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    title: str
    section: str | None
    content: str
    score: float

    def to_source(self, snippet_chars: int = 240) -> dict:
        """Compact form stored on the ticket and shown to the customer as a citation."""
        snippet = self.content if len(self.content) <= snippet_chars else self.content[:snippet_chars].rsplit(" ", 1)[0] + "…"
        return {"title": self.title, "section": self.section, "snippet": snippet, "score": round(self.score, 3)}


def search(db: Session, query: str, k: int | None = None) -> list[RetrievedChunk]:
    k = k or get_settings().rag_top_k
    query_vector = embeddings.get_embedder().embed_query(query)
    distance = KBChunk.embedding.cosine_distance(query_vector).label("distance")

    stmt = (
        select(KBChunk, KBDocument.title, distance)
        .join(KBDocument, KBChunk.document_id == KBDocument.id)
        .where(KBDocument.status == KBStatus.ready)
        .order_by(distance)
        .limit(k)
    )
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            title=title,
            section=chunk.section,
            content=chunk.content,
            score=float(1 - dist),
        )
        for chunk, title, dist in db.execute(stmt).all()
    ]


class KnowledgeBaseRetriever(BaseRetriever):
    """LangChain-compatible retriever, so the KB can plug into any LangChain chain / agent."""

    k: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        with SessionLocal() as db:
            results = search(db, query, self.k)
        return [
            Document(page_content=r.content, metadata={"title": r.title, "section": r.section, "score": r.score})
            for r in results
        ]
