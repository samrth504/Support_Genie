from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.ticket import Ticket, TicketPriority, TicketStatus


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=4000)

    @field_validator("subject", "body")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Too short")
        return v


class Source(BaseModel):
    title: str
    section: str | None = None
    snippet: str
    score: float


RESOLVED = {TicketStatus.ai_resolved, TicketStatus.agent_resolved, TicketStatus.rejected}


class CustomerTicketOut(BaseModel):
    """What a CUSTOMER sees. No internal fields (confidence, draft, flags)."""

    id: int
    subject: str
    body: str
    status: TicketStatus
    category: str | None
    reply: str | None
    answered_by: Literal["ai", "agent"] | None
    sources: list[Source]
    feedback: int | None
    created_at: datetime
    resolved_at: datetime | None

    @classmethod
    def from_ticket(cls, t: Ticket, feedback: int | None = None) -> "CustomerTicketOut":
        resolved = t.status in RESOLVED
        answered_by = None
        if resolved:
            answered_by = "ai" if t.status == TicketStatus.ai_resolved else "agent"
        return cls(
            id=t.id, subject=t.subject, body=t.body, status=t.status, category=t.category,
            reply=t.final_reply if resolved else None,
            answered_by=answered_by,
            sources=(t.sources or []) if t.status == TicketStatus.ai_resolved else [],
            feedback=feedback, created_at=t.created_at, resolved_at=t.resolved_at,
        )


class StaffTicketOut(BaseModel):
    """Everything staff need to review a ticket."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    customer_name: str | None = None
    customer_email: str | None = None
    subject: str
    body: str
    body_masked: str | None
    status: TicketStatus
    priority: TicketPriority
    category: str | None
    category_prob: float | None
    sentiment: str | None
    language: str | None
    confidence: float | None
    injection_flag: bool
    review_reasons: list[str] | None
    ai_draft: str | None
    final_reply: str | None
    sources: list[Source] | None
    reviewed_by: int | None
    created_at: datetime
    resolved_at: datetime | None

    @classmethod
    def from_ticket(cls, t: Ticket) -> "StaffTicketOut":
        out = cls.model_validate(t)
        if t.customer is not None:
            out.customer_name, out.customer_email = t.customer.name, t.customer.email
        return out


class FeedbackIn(BaseModel):
    rating: Literal[1, -1]


class ReviewAction(BaseModel):
    action: Literal["approve", "edit", "reject"]
    reply: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def edit_needs_reply(self) -> "ReviewAction":
        if self.reply is not None:
            self.reply = self.reply.strip() or None
        if self.action == "edit" and not self.reply:
            raise ValueError("'edit' requires a reply")
        return self
