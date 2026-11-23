"""RAG retrieval demo against the real Neon database (run after seed_kb).

    python -m scripts.rag_demo                       # runs the built-in test questions
    python -m scripts.rag_demo "refund kab milega"   # ask your own question

For each question it prints the top chunks and their similarity score.
The last questions are about topics we deliberately did NOT document
(gift cards, international shipping) -> their top score should be clearly lower.
That low score is how the agent will detect a "knowledge gap".
"""
import sys
import time

from app.core.db import SessionLocal
from app.services.rag.retriever import search

QUESTIONS = [
    ("how many days does a UPI refund take", "Refunds and Returns Help"),
    ("I forgot my password", "Account Help"),
    ("can I change the delivery address after the order is shipped", "Shipping Address Help"),
    ("is cash on delivery available for 15000 rupees order", "Payments Help"),
    ("which cities have same day delivery", "Delivery Help"),
    ("early termination fee for plus membership", "Cancellation Help"),
    ("need GST invoice for my company", "Invoices Help"),
    ("mera refund kab aayega", "Refunds and Returns Help"),
    # Not covered by the KB on purpose:
    ("how do I redeem a gift card", None),
    ("do you ship to Dubai", None),
]


def show(question: str, expected: str | None, k: int = 3) -> None:
    with SessionLocal() as db:
        t0 = time.perf_counter()
        hits = search(db, question, k=k)
        ms = (time.perf_counter() - t0) * 1000
    top = hits[0] if hits else None
    verdict = ""
    if expected:
        verdict = "OK " if top and top.title == expected else "XX "
    else:
        verdict = "GAP"
    print(f"\n[{verdict}] Q: {question}   ({ms:.0f} ms)")
    for h in hits:
        print(f"   {h.score:.3f}  {h.title} > {h.section}")


def main() -> None:
    if len(sys.argv) > 1:
        show(" ".join(sys.argv[1:]), None, k=5)
        return
    for q, expected in QUESTIONS:
        show(q, expected)


if __name__ == "__main__":
    main()
