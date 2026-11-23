import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin
from app.models.user import User


class TicketStatus(str, enum.Enum):
    open = "open"                       # just created, agent not finished yet
    ai_resolved = "ai_resolved"         # auto-replied by the AI
    pending_review = "pending_review"   # paused, waiting for a staff member
    agent_resolved = "agent_resolved"   # staff approved / edited the reply
    rejected = "rejected"               # staff rejected (e.g. spam / injection)


class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    # What the customer wrote (body_masked = PII removed; only this goes to the LLM)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_masked: Mapped[str | None] = mapped_column(Text)

    # ML + agent results
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    category_prob: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False, length=20), default=TicketPriority.medium, nullable=False
    )
    sentiment: Mapped[str | None] = mapped_column(String(20))
    language: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None] = mapped_column(Float)
    injection_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Replies
    ai_draft: Mapped[str | None] = mapped_column(Text)
    final_reply: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list | None] = mapped_column(JSON)      # [{"title":..., "snippet":..., "score":...}]

    # Workflow
    review_reasons: Mapped[list | None] = mapped_column(JSON)   # why the agent asked a human
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False, length=20), default=TicketStatus.open, index=True, nullable=False
    )
    thread_id: Mapped[str | None] = mapped_column(String(64), unique=True)   # LangGraph run id (resume after review)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])
