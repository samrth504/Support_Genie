import enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import get_settings
from app.core.db import Base
from app.models.mixins import TimestampMixin

EMBEDDING_DIM = get_settings().embedding_dim


class KBStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class KBDocument(TimestampMixin, Base):
    """One uploaded help document."""

    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[KBStatus] = mapped_column(
        Enum(KBStatus, native_enum=False, length=20), default=KBStatus.processing, nullable=False
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    chunks: Mapped[list["KBChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class KBChunk(Base):
    """One piece of a document + its embedding vector (pgvector column)."""

    __tablename__ = "kb_chunks"
    __table_args__ = (
        # HNSW = fast approximate nearest-neighbour index for cosine distance (Postgres only;
        # the postgresql_* options are ignored by SQLite in tests)
        Index(
            "ix_kb_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("kb_documents.id", ondelete="CASCADE"), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)

    document: Mapped[KBDocument] = relationship(back_populates="chunks")
