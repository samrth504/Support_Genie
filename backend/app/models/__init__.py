"""Import every model here so Base.metadata knows all tables (needed by Alembic)."""
from app.models.feedback import Feedback
from app.models.kb import KBChunk, KBDocument, KBStatus
from app.models.knowledge_gap import KnowledgeGap
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole

__all__ = [
    "Feedback",
    "KBChunk",
    "KBDocument",
    "KBStatus",
    "KnowledgeGap",
    "Ticket",
    "TicketPriority",
    "TicketStatus",
    "User",
    "UserRole",
]
