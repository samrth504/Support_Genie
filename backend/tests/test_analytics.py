"""Analytics: KPIs, K-means trends, knowledge gaps."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.feedback import Feedback
from app.models.knowledge_gap import KnowledgeGap
from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole
from app.services.rag import embeddings
from tests.conftest import login

DIM = get_settings().embedding_dim


class BagOfWordsEmbedder:
    def _vec(self, text):
        v = [0.0] * DIM
        for w in text.lower().replace(".", " ").replace(",", " ").split():
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
        return v

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]


@pytest.fixture
def staff(client: TestClient, staff_user: dict) -> dict:
    return {"Authorization": f"Bearer {login(client, staff_user['email'], staff_user['password'])}"}


def _customer_id() -> int:
    with SessionLocal() as db:
        u = User(name="Rahul", email="rahul@shopnest.com", password_hash=hash_password("Password123"), role=UserRole.customer)
        db.add(u)
        db.commit()
        return u.id


def _add_tickets(rows: list[tuple[str, str, TicketStatus, str]]) -> list[int]:
    cid = _customer_id()
    now = datetime.now(timezone.utc)
    ids = []
    with SessionLocal() as db:
        for subject, body, status, category in rows:
            resolved = now + timedelta(seconds=3) if status in (TicketStatus.ai_resolved, TicketStatus.agent_resolved) else None
            t = Ticket(customer_id=cid, subject=subject, body=body, body_masked=body, status=status,
                       category=category, confidence=0.8, created_at=now, resolved_at=resolved)
            db.add(t)
            db.flush()
            ids.append(t.id)
        db.commit()
    return ids


def test_summary_kpis(client, staff):
    ids = _add_tickets([
        ("Reset password", "forgot my password", TicketStatus.ai_resolved, "ACCOUNT"),
        ("Delivery time", "how long is delivery", TicketStatus.ai_resolved, "DELIVERY"),
        ("Refund missing", "where is my refund", TicketStatus.pending_review, "REFUND"),
        ("Charged twice", "charged twice", TicketStatus.agent_resolved, "PAYMENT"),
    ])
    with SessionLocal() as db:
        db.add_all([Feedback(ticket_id=ids[0], rating=1), Feedback(ticket_id=ids[1], rating=-1)])
        db.add(KnowledgeGap(ticket_id=ids[2], query="gift card", top_score=0.6))
        db.commit()

    s = client.get("/api/analytics/summary", headers=staff).json()
    assert s["total_tickets"] == 4
    assert s["by_status"]["ai_resolved"] == 2
    assert s["auto_resolution_rate"] == 0.5
    assert s["pending_review"] == 1
    assert s["feedback"] == {"positive": 1, "negative": 1, "satisfaction_rate": 0.5}
    assert s["knowledge_gaps"] == 1
    assert s["avg_ai_response_seconds"] == pytest.approx(3, abs=1)
    assert len(s["tickets_per_day"]) == 14 and s["tickets_per_day"][-1]["count"] == 4
    assert {c["category"] for c in s["by_category"]} == {"ACCOUNT", "DELIVERY", "REFUND", "PAYMENT"}


def test_trends_groups_similar_tickets(client, staff, monkeypatch):
    monkeypatch.setattr(embeddings, "get_embedder", lambda: BagOfWordsEmbedder())
    refund = [(f"Refund issue {i}", "my refund money is not credited to bank account yet refund", TicketStatus.pending_review, "REFUND") for i in range(6)]
    password = [(f"Login issue {i}", "cannot login password reset link expired password", TicketStatus.ai_resolved, "ACCOUNT") for i in range(6)]
    ids = _add_tickets(refund + password)
    refund_ids, password_ids = set(ids[:6]), set(ids[6:])

    t = client.get("/api/analytics/trends", headers=staff).json()
    assert t["tickets_analysed"] == 12 and t["k"] >= 2
    assert sum(c["size"] for c in t["clusters"]) == 12
    for c in t["clusters"]:                       # every cluster is "pure": only refunds OR only logins
        members = set(c["ticket_ids"])
        assert members <= refund_ids or members <= password_ids
        assert c["label"]                          # keyword fallback name (no LLM in tests)
    all_keywords = " ".join(" ".join(c["keywords"]) for c in t["clusters"])
    assert "refund" in all_keywords and "password" in all_keywords


def test_trends_needs_enough_tickets(client, staff):
    _add_tickets([("Hi", "where is my order", TicketStatus.ai_resolved, "ORDER")])
    t = client.get("/api/analytics/trends", headers=staff).json()
    assert t["clusters"] == [] and "at least 6" in t["message"]


def test_gaps_list_and_permissions(client, staff):
    ids = _add_tickets([("Gift card", "redeem gift card", TicketStatus.pending_review, "ACCOUNT")])
    with SessionLocal() as db:
        db.add(KnowledgeGap(ticket_id=ids[0], query="redeem gift card", top_score=0.61))
        db.commit()
    gaps = client.get("/api/analytics/gaps", headers=staff).json()
    assert gaps[0]["subject"] == "Gift card" and gaps[0]["top_score"] == 0.61

    client.post("/api/auth/signup", json={"name": "Priya", "email": "priya@shopnest.com", "password": "Password123"})
    priya = {"Authorization": f"Bearer {login(client, 'priya@shopnest.com', 'Password123')}"}
    for path in ("/api/analytics/summary", "/api/analytics/trends", "/api/analytics/gaps"):
        assert client.get(path, headers=priya).status_code == 403


def test_cluster_keywords_only_use_words_from_that_cluster():
    """Regression: a 1-ticket cluster used to get zero-score words from other clusters ('twice order')."""
    import numpy as np

    from app.services.ml.clustering import _keywords

    texts = ["I forgot my password, how can I reset it?",
             "You charged my card twice for one order", "charged twice, refund my order"]
    kw = _keywords(texts, np.array([0, 1, 1]), k=2)
    assert all(w in {"forgot", "password", "reset", "forgot password", "password reset"}
               or w in "forgot password reset" for w in kw[0])
    assert not any("twice" in w or "order" in w for w in kw[0])
