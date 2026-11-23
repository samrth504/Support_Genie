"""Staff endpoints: review queue + approve / edit / reject (human-in-the-loop)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.security import require_role
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.schemas.ticket import ReviewAction, StaffTicketOut
from app.services.tickets import resume_ticket

router = APIRouter(prefix="/api/review", tags=["review (staff)"])
staff_only = require_role(UserRole.staff)

# high -> medium -> low, then oldest first
_PRIORITY_ORDER = case(
    {TicketPriority.high: 0, TicketPriority.medium: 1, TicketPriority.low: 2}, value=Ticket.priority, else_=3
)


@router.get("/queue", response_model=list[StaffTicketOut])
def review_queue(db: Session = Depends(get_db), _: User = Depends(staff_only)):
    """Tickets waiting for a human, most urgent first."""
    tickets = db.scalars(
        select(Ticket).options(selectinload(Ticket.customer))
        .where(Ticket.status == TicketStatus.pending_review)
        .order_by(_PRIORITY_ORDER, Ticket.created_at.asc(), Ticket.id.asc())
    )
    return [StaffTicketOut.from_ticket(t) for t in tickets]


@router.get("/tickets", response_model=list[StaffTicketOut])
def all_tickets(
    status_filter: TicketStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(staff_only),
):
    stmt = select(Ticket).options(selectinload(Ticket.customer)).order_by(Ticket.created_at.desc(), Ticket.id.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    return [StaffTicketOut.from_ticket(t) for t in db.scalars(stmt)]


@router.get("/tickets/{ticket_id}", response_model=StaffTicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db), _: User = Depends(staff_only)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return StaffTicketOut.from_ticket(ticket)


@router.post("/tickets/{ticket_id}", response_model=StaffTicketOut)
def review_ticket(ticket_id: int, payload: ReviewAction, db: Session = Depends(get_db), staff: User = Depends(staff_only)):
    """approve = send the AI draft as-is (or with optional `reply`) · edit = send `reply` · reject = close."""
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    if ticket.status != TicketStatus.pending_review:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ticket is '{ticket.status.value}', not pending review")
    if payload.action == "approve" and not (payload.reply or ticket.ai_draft):
        raise HTTPException(422, "There is no AI draft for this ticket - use 'edit' and write a reply")
    ticket = resume_ticket(db, ticket, payload.action, payload.reply, staff)
    return StaffTicketOut.from_ticket(ticket)
