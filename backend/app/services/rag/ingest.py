"""Ingestion pipeline: text -> chunks -> embeddings -> kb_chunks table.

Runs as a FastAPI background task (so uploads return instantly) and from the seed script.
"""
import logging

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.kb import KBChunk, KBDocument, KBStatus
from app.services.rag import embeddings
from app.services.rag.chunking import split_text

logger = logging.getLogger(__name__)
EMBED_BATCH_SIZE = 32


def index_document(db: Session, doc: KBDocument, text: str) -> int:
    """Chunk + embed + store. Replaces any existing chunks of this document. Returns chunk count."""
    chunks = split_text(text, doc.title)
    if not chunks:
        raise ValueError("No usable text found in the document")

    embedder = embeddings.get_embedder()
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        vectors.extend(embedder.embed_documents([c.page_content for c in batch]))

    db.execute(delete(KBChunk).where(KBChunk.document_id == doc.id))
    db.add_all(
        KBChunk(
            document_id=doc.id,
            chunk_index=i,
            section=chunk.metadata.get("section"),
            content=chunk.page_content,
            embedding=vector,
            metadata_=chunk.metadata,
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    )
    doc.chunk_count = len(chunks)
    doc.status = KBStatus.ready
    doc.error = None
    db.commit()
    logger.info("Indexed document id=%s '%s' -> %d chunks", doc.id, doc.title, len(chunks))
    return len(chunks)


def index_document_task(document_id: int, text: str) -> None:
    """Background-task entry point: opens its OWN session (the request's session is closed by now)."""
    with SessionLocal() as db:
        doc = db.get(KBDocument, document_id)
        if doc is None:
            logger.warning("Document %s disappeared before indexing", document_id)
            return
        try:
            index_document(db, doc, text)
        except Exception as exc:  # noqa: BLE001 - record any failure on the document
            db.rollback()
            logger.exception("Indexing failed for document id=%s", document_id)
            doc = db.get(KBDocument, document_id)
            if doc is not None:
                doc.status = KBStatus.failed
                doc.error = str(exc)[:1000]
                db.commit()
