"""LangGraph nodes. One function = one step. Each returns only the state keys it changes."""
import logging

from langgraph.types import interrupt

from app.agent import policy
from app.agent.prompts import DRAFT_PROMPT, DraftOutput, format_context
from app.agent.state import AgentState
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services import llm
from app.services.guard import run_guard
from app.services.ml import classifier
from app.services.rag import retriever

logger = logging.getLogger(__name__)


def _draft_chain():
    """prompt | LLM (structured output, retry, Groq -> Gemini fallback)."""
    return DRAFT_PROMPT | llm.structured_llm(DraftOutput)


# 1 ----------------------------------------------------------------- guard
def guard_node(state: AgentState) -> AgentState:
    result = run_guard(f"{state['subject']}\n{state['body']}")
    if result.injection_flag:
        logger.warning("Prompt injection suspected in ticket %s: %r", state["ticket_id"], result.injection_match)
    return {"masked_text": result.masked_text, "pii_found": result.pii_found, "injection_flag": result.injection_flag}


# 2 ----------------------------------------------------------------- classify
def classify_node(state: AgentState) -> AgentState:
    pred = classifier.predict(state["masked_text"])
    return {"category": pred.category, "category_prob": round(pred.probability, 3)}


# 3 ----------------------------------------------------------------- retrieve
def retrieve_node(state: AgentState) -> AgentState:
    with SessionLocal() as db:
        hits = retriever.search(db, state["masked_text"], k=get_settings().rag_top_k)
    chunks = [{"title": h.title, "section": h.section, "content": h.content, "score": round(h.score, 4)} for h in hits]
    top = chunks[0]["score"] if chunks else 0.0
    return {"retrieved": chunks, "top_score": top, "knowledge_gap": top < policy.KNOWLEDGE_GAP_SCORE}


# 4 ----------------------------------------------------------------- draft (the ONLY LLM call)
def draft_node(state: AgentState) -> AgentState:
    subject, _, message = state["masked_text"].partition("\n")
    try:
        draft: DraftOutput = _draft_chain().invoke({
            "context": format_context(state.get("retrieved", [])),
            "category": state.get("category", "UNKNOWN"),
            "subject": subject,
            "message": message,
        })
    except Exception as exc:  # noqa: BLE001 - both providers failed / no key -> a human handles it
        logger.exception("LLM draft failed for ticket %s", state["ticket_id"])
        return {"draft": None, "llm_error": f"{type(exc).__name__}: {exc}"[:500]}

    updates: AgentState = {"draft": draft.model_dump(), "llm_error": None}
    if not draft.answer_found:
        updates["knowledge_gap"] = True
    return updates


# 5 ----------------------------------------------------------------- route (all decisions)
def route_node(state: AgentState) -> AgentState:
    draft = state.get("draft") or {}
    category = state.get("category")
    sentiment = draft.get("sentiment")
    reasons: list[str] = []

    if state.get("injection_flag"):
        reasons.append("prompt_injection_suspected")
    if not draft:
        reasons.append("ai_draft_unavailable")
    else:
        if not draft["answer_found"]:
            reasons.append("answer_not_in_knowledge_base")
        if sentiment == "frustrated":
            reasons.append("frustrated_customer")
        if draft["requires_human_action"]:
            reasons.append("needs_account_action")
    if not state.get("injection_flag") and policy.is_money_problem(state.get("masked_text", "")):
        reasons.append("money_problem_needs_human")

    confidence = policy.compute_confidence(
        llm_conf=draft.get("self_confidence", 0.0),
        top_score=state.get("top_score", 0.0),
        classifier_prob=state.get("category_prob", 0.0),
    )
    high_risk = policy.is_high_risk(category, state.get("masked_text", ""))
    threshold = policy.MIN_CONFIDENCE_HIGH_RISK if high_risk else policy.MIN_CONFIDENCE
    if draft and confidence < threshold:
        reasons.append(f"low_confidence_{confidence:.2f}_below_{threshold:.2f}")

    priority = policy.compute_priority(category, sentiment, state.get("masked_text", ""), bool(state.get("injection_flag")))
    decision = "human_review" if reasons else "auto_reply"
    logger.info("Ticket %s -> %s (confidence=%.2f, category=%s, reasons=%s)",
                state["ticket_id"], decision, confidence, category, reasons)
    return {"confidence": confidence, "priority": priority, "review_reasons": reasons, "decision": decision}


# 6a ---------------------------------------------------------------- auto reply
def auto_reply_node(state: AgentState) -> AgentState:
    return {"final_reply": state["draft"]["reply"], "status": "ai_resolved"}


# 6b ---------------------------------------------------------------- human review (PAUSE)
def human_review_node(state: AgentState) -> AgentState:
    """interrupt() saves the whole state in the Postgres checkpointer and STOPS the graph.
    When staff decide (POST /api/review/tickets/{id}) the graph is resumed with
    Command(resume={...}) and interrupt() returns that dict right here."""
    draft = state.get("draft") or {}
    review = interrupt({
        "ticket_id": state["ticket_id"],
        "draft": draft.get("reply"),
        "reasons": state.get("review_reasons", []),
    })

    action = review.get("action")
    if action == "reject":
        return {"review": review, "status": "rejected", "final_reply": review.get("reply") or policy.REJECT_MESSAGE}
    reply = review.get("reply") if action == "edit" else (review.get("reply") or draft.get("reply"))
    return {"review": review, "status": "agent_resolved", "final_reply": reply}
