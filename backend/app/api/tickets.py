"""Customer ticket endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.rate_limit import ticket_limiter
from app.core.security import require_role
from app.models.feedback import Feedback
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import CustomerTicketOut, FeedbackIn, TicketCreate
from app.services.tickets import process_ticket

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tickets", tags=["tickets (customer)"])
customer_only = require_role(UserRole.customer)


def _own_ticket(db: Session, ticket_id: int, user: User) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    # 404 (not 403) for other people's tickets -> doesn't reveal that the ticket exists
    if ticket is None or ticket.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


def _feedback_of(db: Session, ticket_id: int) -> int | None:
    return db.scalar(select(Feedback.rating).where(Feedback.ticket_id == ticket_id))


@router.post("", response_model=CustomerTicketOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(ticket_limiter)])
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    """Creates the ticket and runs the AI agent (takes a few seconds).
    Result is either an instant AI reply (`ai_resolved`) or `pending_review` for a human agent."""
    ticket = Ticket(customer_id=user.id, subject=payload.subject, body=payload.body, status=TicketStatus.open)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    ticket = process_ticket(db, ticket)
    return CustomerTicketOut.from_ticket(ticket)


@router.get("", response_model=list[CustomerTicketOut])
def list_my_tickets(db: Session = Depends(get_db), user: User = Depends(customer_only)):
    tickets = db.scalars(select(Ticket).where(Ticket.customer_id == user.id).order_by(Ticket.created_at.desc(), Ticket.id.desc()))
    ratings = dict(db.execute(select(Feedback.ticket_id, Feedback.rating).join(Ticket).where(Ticket.customer_id == user.id)).all())
    return [CustomerTicketOut.from_ticket(t, ratings.get(t.id)) for t in tickets]


@router.get("/{ticket_id}", response_model=CustomerTicketOut)
def get_my_ticket(ticket_id: int, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    ticket = _own_ticket(db, ticket_id, user)
    return CustomerTicketOut.from_ticket(ticket, _feedback_of(db, ticket.id))


@router.post("/{ticket_id}/feedback", response_model=CustomerTicketOut)
def give_feedback(ticket_id: int, payload: FeedbackIn, db: Session = Depends(get_db), user: User = Depends(customer_only)):
    """👍 (+1) / 👎 (-1). A 👎 on an AI answer escalates the ticket to a human."""
    ticket = _own_ticket(db, ticket_id, user)
    if ticket.status not in (TicketStatus.ai_resolved, TicketStatus.agent_resolved):
        raise HTTPException(status.HTTP_409_CONFLICT, "Feedback is only possible on answered tickets")
    if _feedback_of(db, ticket.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Feedback already given for this ticket")

    db.add(Feedback(ticket_id=ticket.id, rating=payload.rating))
    if payload.rating == -1 and ticket.status == TicketStatus.ai_resolved:
        ticket.status = TicketStatus.pending_review
        ticket.priority = TicketPriority.high
        ticket.review_reasons = [*(ticket.review_reasons or []), "customer_unhappy_with_ai_answer"]
        ticket.resolved_at = None
        logger.info("Ticket %s escalated after negative feedback", ticket.id)
    db.commit()
    db.refresh(ticket)
    return CustomerTicketOut.from_ticket(ticket, payload.rating)
