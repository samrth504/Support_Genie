"""Knowledge-base management (staff only): upload, list, delete, test search."""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import require_role
from app.models.kb import KBDocument, KBStatus
from app.models.user import User, UserRole
from app.schemas.kb import KBDocumentOut, SearchHit, SearchResponse
from app.services.rag.ingest import index_document_task
from app.services.rag.loaders import UnsupportedFileError, extract_text, guess_title
from app.services.rag.retriever import search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kb", tags=["knowledge base"])
staff_only = require_role(UserRole.staff)


@router.post("/upload", response_model=KBDocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(staff_only),
) -> KBDocument:
    """Upload a .md / .txt / .pdf help document. Returns immediately with status 'processing';
    chunking + embedding run in the background. Poll GET /api/kb/documents to see 'ready'."""
    max_bytes = get_settings().kb_max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File is larger than {get_settings().kb_max_upload_mb} MB")

    filename = (file.filename or "document.txt").strip()
    if db.scalar(select(KBDocument).where(KBDocument.filename == filename)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{filename}' already exists. Delete it first to re-upload.")

    try:
        text = extract_text(filename, data)
    except UnsupportedFileError as exc:
        raise HTTPException(422, str(exc))
    except Exception:  # corrupted PDF etc.
        logger.exception("Could not read uploaded file %s", filename)
        raise HTTPException(422, "Could not read this file")

    doc = KBDocument(filename=filename, title=guess_title(filename, text), status=KBStatus.processing,
                     uploaded_by=user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background_tasks.add_task(index_document_task, doc.id, text)
    logger.info("KB upload accepted: id=%s file=%s by user=%s", doc.id, filename, user.id)
    return doc


@router.get("/documents", response_model=list[KBDocumentOut])
def list_documents(db: Session = Depends(get_db), _: User = Depends(staff_only)) -> list[KBDocument]:
    return list(db.scalars(select(KBDocument).order_by(KBDocument.created_at.desc(), KBDocument.id.desc())))


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db), _: User = Depends(staff_only)) -> None:
    doc = db.get(KBDocument, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    db.delete(doc)  # chunks are deleted too (ON DELETE CASCADE)
    db.commit()
    logger.info("KB document deleted: id=%s", document_id)


@router.get("/search", response_model=SearchResponse)
def search_kb(
    q: str = Query(min_length=2, max_length=500),
    k: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    _: User = Depends(staff_only),
) -> SearchResponse:
    """Debug / demo endpoint: see exactly which chunks RAG would give the LLM for a question."""
    hits = search(db, q, k)
    return SearchResponse(
        query=q,
        results=[SearchHit(title=h.title, section=h.section, content=h.content, score=round(h.score, 4)) for h in hits],
    )
