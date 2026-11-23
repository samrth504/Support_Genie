"""Numbers for the staff dashboard: KPIs, trends (K-means) and knowledge gaps."""
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.kb import KBChunk, KBDocument, KBStatus
from app.models.knowledge_gap import KnowledgeGap
from app.models.ticket import Ticket, TicketStatus
from app.services import llm
from app.services.guard import mask_pii
from app.services.ml.clustering import cluster_tickets
from app.services.rag import embeddings

logger = logging.getLogger(__name__)
MAX_TICKETS_FOR_TRENDS = 300


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _avg_seconds(pairs: list[tuple[datetime, datetime]]) -> float | None:
    if not pairs:
        return None
    return round(sum((_utc(r) - _utc(c)).total_seconds() for c, r in pairs) / len(pairs), 1)


# ------------------------------------------------------------------ KPIs
def summary(db: Session, days: int = 14) -> dict:
    by_status = dict(db.execute(select(Ticket.status, func.count()).group_by(Ticket.status)).all())
    counts = {s.value: int(by_status.get(s, 0)) for s in TicketStatus}
    total = sum(counts.values())
    handled = total - counts["open"]
    ai = counts["ai_resolved"]

    by_category = [
        {"category": c or "UNKNOWN", "count": int(n)}
        for c, n in db.execute(select(Ticket.category, func.count()).group_by(Ticket.category).order_by(func.count().desc())).all()
    ]
    by_priority = {p.value if hasattr(p, "value") else p: int(n)
                   for p, n in db.execute(select(Ticket.priority, func.count()).group_by(Ticket.priority)).all()}

    ratings = dict(db.execute(select(Feedback.rating, func.count()).group_by(Feedback.rating)).all())
    up, down = int(ratings.get(1, 0)), int(ratings.get(-1, 0))

    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    day_col = func.date(Ticket.created_at)
    per_day_rows = dict(
        (str(d), int(n)) for d, n in db.execute(
            select(day_col, func.count()).where(Ticket.created_at >= since.replace(hour=0, minute=0, second=0, microsecond=0))
            .group_by(day_col)
        ).all()
    )
    per_day = []
    for i in range(days):
        d = (since + timedelta(days=i)).date().isoformat()
        per_day.append({"date": d, "count": per_day_rows.get(d, 0)})

    resolved = db.execute(select(Ticket.status, Ticket.created_at, Ticket.resolved_at)
                          .where(Ticket.resolved_at.is_not(None))).all()
    ai_times = [(c, r) for s, c, r in resolved if s == TicketStatus.ai_resolved]
    agent_times = [(c, r) for s, c, r in resolved if s == TicketStatus.agent_resolved]

    avg_conf = db.scalar(select(func.avg(Ticket.confidence)).where(Ticket.confidence.is_not(None)))
    return {
        "total_tickets": total,
        "by_status": counts,
        "auto_resolution_rate": round(ai / handled, 3) if handled else None,
        "pending_review": counts["pending_review"],
        "avg_confidence": round(float(avg_conf), 3) if avg_conf is not None else None,
        "avg_ai_response_seconds": _avg_seconds(ai_times),
        "avg_agent_response_seconds": _avg_seconds(agent_times),
        "feedback": {"positive": up, "negative": down,
                     "satisfaction_rate": round(up / (up + down), 3) if (up + down) else None},
        "by_category": by_category,
        "by_priority": by_priority,
        "tickets_per_day": per_day,
        "knowledge_base": {
            "documents": int(db.scalar(select(func.count()).select_from(KBDocument).where(KBDocument.status == KBStatus.ready)) or 0),
            "chunks": int(db.scalar(select(func.count()).select_from(KBChunk)) or 0),
        },
        "knowledge_gaps": int(db.scalar(select(func.count()).select_from(KnowledgeGap)) or 0),
    }


# ------------------------------------------------------------------ trends (K-means)
class ClusterNames(BaseModel):
    names: list[str] = Field(description="One short issue name (2-5 words) per cluster, in the same order")


_NAMING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You name groups of customer-support tickets for a dashboard. Give each group a short, specific "
               "issue name of 2-5 words, like 'Duplicate UPI charges' or 'Password reset problems'. "
               "Return exactly one name per group, in order."),
    ("human", "{groups}"),
])


def _name_clusters(groups: list[dict]) -> list[str]:
    """One LLM call for ALL clusters. Falls back to keywords if no LLM is available."""
    fallback = [" / ".join(g["keywords"][:3]).title() or f"Cluster {i + 1}" for i, g in enumerate(groups)]
    try:
        text = "\n\n".join(
            f"Group {i + 1}: keywords = {', '.join(g['keywords'])}\nexample subjects: {' | '.join(g['examples'])}"
            for i, g in enumerate(groups)
        )
        result: ClusterNames = (_NAMING_PROMPT | llm.structured_llm(ClusterNames)).invoke({"groups": text})
        if len(result.names) == len(groups):
            return [n.strip()[:60] or fallback[i] for i, n in enumerate(result.names)]
    except Exception as exc:  # noqa: BLE001 - naming is cosmetic
        logger.info("Cluster naming fell back to keywords: %s", exc)
    return fallback


def trends(db: Session, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    tickets = list(db.scalars(select(Ticket).where(Ticket.created_at >= since)
                              .order_by(Ticket.created_at.desc()).limit(MAX_TICKETS_FOR_TRENDS)))
    texts = [mask_pii(f"{t.subject}. {t.body_masked or t.body}")[0] for t in tickets]

    base = {"days": days, "tickets_analysed": len(tickets)}
    if len(tickets) < 6:
        return {**base, "k": 0, "silhouette": None, "clusters": [],
                "message": "Need at least 6 tickets in this period to find trends."}

    vectors = embeddings.get_embedder().embed_documents(texts)
    result = cluster_tickets(texts, vectors)
    if result is None:
        return {**base, "k": 0, "silhouette": None, "clusters": [], "message": "Could not find clear clusters."}

    groups = []
    for c in range(result.k):
        members = [t for t, lbl in zip(tickets, result.labels) if lbl == c]
        cats = Counter(t.category for t in members if t.category)
        groups.append({
            "cluster_id": c,
            "size": len(members),
            "share": round(len(members) / len(tickets), 3),
            "keywords": result.keywords[c],
            "top_category": cats.most_common(1)[0][0] if cats else None,
            "pending_review": sum(t.status == TicketStatus.pending_review for t in members),
            "examples": [mask_pii(t.subject)[0] for t in members[:3]],
            "ticket_ids": [t.id for t in members[:20]],
        })
    for g, name in zip(groups, _name_clusters(groups)):
        g["label"] = name
    groups.sort(key=lambda g: g["size"], reverse=True)
    return {**base, "k": result.k, "silhouette": result.silhouette, "clusters": groups}


# ------------------------------------------------------------------ knowledge gaps
def knowledge_gaps(db: Session, limit: int = 50) -> list[dict]:
    rows = db.execute(
        select(KnowledgeGap, Ticket.subject, Ticket.category)
        .outerjoin(Ticket, KnowledgeGap.ticket_id == Ticket.id)
        .order_by(KnowledgeGap.created_at.desc(), KnowledgeGap.id.desc()).limit(limit)
    ).all()
    return [
        {"id": g.id, "ticket_id": g.ticket_id, "subject": mask_pii(subject)[0] if subject else None,
         "category": category, "query": g.query[:300], "top_score": g.top_score, "created_at": g.created_at}
        for g, subject, category in rows
    ]
