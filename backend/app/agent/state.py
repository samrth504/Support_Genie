"""The shared 'notebook' that flows through every LangGraph node.

Each node reads what it needs and returns ONLY the keys it wants to update.
"""
from typing import Any, Literal, TypedDict


class AgentState(TypedDict, total=False):
    # input
    ticket_id: int
    subject: str
    body: str

    # guard
    masked_text: str
    pii_found: list[str]
    injection_flag: bool

    # classify (ML model)
    category: str
    category_prob: float

    # retrieve (RAG)
    retrieved: list[dict[str, Any]]      # [{title, section, content, score}]
    top_score: float
    knowledge_gap: bool

    # draft (LLM)
    draft: dict[str, Any] | None         # DraftOutput.model_dump()
    llm_error: str | None

    # route (decision)
    confidence: float
    priority: Literal["low", "medium", "high"]
    review_reasons: list[str]
    decision: Literal["auto_reply", "human_review"]

    # result
    review: dict[str, Any] | None        # what the staff member decided
    final_reply: str | None
    status: str
