"""Runs the LangGraph agent for a ticket and saves the outcome. The API layer stays thin.

process_ticket() -> first run (may end in auto-reply, or pause at human_review)
resume_ticket()  -> staff decision resumes the paused graph from its checkpoint
"""
import logging
import uuid
from datetime import datetime, timezone

from langgraph.types import Command
from sqlalchemy.orm import Session

from app.agent.graph import get_agent
from app.agent.policy import REJECT_MESSAGE
from app.models.knowledge_gap import KnowledgeGap
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User

logger = logging.getLogger(__name__)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _apply_state(ticket: Ticket, state: dict) -> None:
    masked = state.get("masked_text")
    if masked is not None:
        ticket.body_masked = masked.partition("\n")[2]
    ticket.category = state.get("category", ticket.category)
    ticket.category_prob = state.get("category_prob", ticket.category_prob)
    ticket.injection_flag = bool(state.get("injection_flag", ticket.injection_flag))
    ticket.confidence = state.get("confidence", ticket.confidence)
    if state.get("priority"):
        ticket.priority = TicketPriority(state["priority"])
    ticket.review_reasons = state.get("review_reasons", ticket.review_reasons)

    draft = state.get("draft") or {}
    if draft:
        ticket.ai_draft = draft.get("reply")
        ticket.sentiment = draft.get("sentiment")
        ticket.language = draft.get("language")
        used = set(draft.get("used_sources") or [])
        chunks = state.get("retrieved") or []
        picked = [c for i, c in enumerate(chunks, start=1) if not used or i in used]
        ticket.sources = [
            {"title": c["title"], "section": c.get("section"), "snippet": c["content"][:240], "score": c["score"]}
            for c in picked[:3]
        ]


def process_ticket(db: Session, ticket: Ticket) -> Ticket:
    agent = get_agent()
    ticket.thread_id = f"ticket-{ticket.id}-{uuid.uuid4().hex[:8]}"
    config = _config(ticket.thread_id)

    try:
        agent.invoke({"ticket_id": ticket.id, "subject": ticket.subject, "body": ticket.body}, config)
        snapshot = agent.get_state(config)
    except Exception:  # noqa: BLE001 - never lose a ticket: a human will handle it
        logger.exception("Agent crashed on ticket %s", ticket.id)
        ticket.status = TicketStatus.pending_review
        ticket.review_reasons = ["agent_error"]
        db.commit()
        return ticket

    state = snapshot.values
    _apply_state(ticket, state)
    paused = bool(snapshot.next)  # graph stopped at human_review

    if paused:
        ticket.status = TicketStatus.pending_review
    else:
        ticket.status = TicketStatus(state.get("status", TicketStatus.ai_resolved.value))
        ticket.final_reply = state.get("final_reply")
        ticket.resolved_at = datetime.now(timezone.utc)

    if state.get("knowledge_gap") and not state.get("injection_flag"):
        db.add(KnowledgeGap(ticket_id=ticket.id, query=(state.get("masked_text") or ticket.body)[:1000],
                            top_score=state.get("top_score")))
    db.commit()
    db.refresh(ticket)
    return ticket


def resume_ticket(db: Session, ticket: Ticket, action: str, reply: str | None, reviewer: User) -> Ticket:
    """Apply a staff decision. If the graph is paused, resume it; otherwise (agent error, or
    escalated by 👎 after an auto-reply) apply the decision directly."""
    agent = get_agent()
    resumed = False
    if ticket.thread_id:
        config = _config(ticket.thread_id)
        snapshot = agent.get_state(config)
        if snapshot.next:
            agent.invoke(Command(resume={"action": action, "reply": reply, "reviewer_id": reviewer.id}), config)
            state = agent.get_state(config).values
            ticket.status = TicketStatus(state["status"])
            ticket.final_reply = state.get("final_reply")
            resumed = True

    if not resumed:
        if action == "reject":
            ticket.status, ticket.final_reply = TicketStatus.rejected, reply or REJECT_MESSAGE
        else:
            ticket.status = TicketStatus.agent_resolved
            ticket.final_reply = reply if action == "edit" else (reply or ticket.ai_draft)

    ticket.reviewed_by = reviewer.id
    ticket.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    logger.info("Ticket %s reviewed by user %s: %s (graph resumed=%s)", ticket.id, reviewer.id, action, resumed)
    return ticket
