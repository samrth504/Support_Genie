from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class KnowledgeGap(Base):
    """A question the knowledge base could not answer well (low retrieval similarity).
    Shown to staff so they know which help docs to write next."""

    __tablename__ = "knowledge_gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"), index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    top_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
