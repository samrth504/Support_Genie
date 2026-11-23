"""Fill the database with a realistic demo dataset (for the dashboard, trends and the viva).

    python -m scripts.seed_demo_data              # ~37 tickets through the REAL agent
    python -m scripts.seed_demo_data --delay 10   # slower, if Groq returns rate-limit errors
    python -m scripts.seed_demo_data --reset      # delete previous demo data first

What it does:
1. Creates 3 demo customers (Rahul, Priya, Arjun; password Demo12345).
2. Sends ~37 tickets in 7 themes (several similar tickets per theme, English + Hinglish)
   through the real LangGraph agent: real ML classifier, RAG on Neon and the Groq LLM.
3. An existing STAFF user approves ~60% of the pending tickets (so agent response time exists).
4. Customers leave feedback on answered tickets (mostly 👍, a few 👎 -> escalations).

Needs: a staff account (python -m scripts.create_staff ...) and GROQ_API_KEY in .env.
Free-tier note: Groq limits tokens per minute, so tickets are sent with a pause (--delay).
"""
import argparse
import random
import time

from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.core.security import hash_password
from app.models.feedback import Feedback
from app.models.knowledge_gap import KnowledgeGap
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.models.user import User, UserRole
from app.services.tickets import process_ticket, resume_ticket

CUSTOMERS = [
    ("Rahul Verma", "rahul.demo@shopnest.com"),
    ("Priya Sharma", "priya.demo@shopnest.com"),
    ("Arjun Mehta", "arjun.demo@shopnest.com"),
]
PASSWORD = "Demo12345"

THEMES = {
    "refund_delay": [
        ("Refund not received", "I returned my shoes 6 days ago and the pickup was done, but I still have not received my refund. I paid by credit card."),
        ("Where is my refund?", "My return was picked up last week. How many days does the refund take for UPI payments?"),
        ("Refund status", "Return quality check is done but refund is not showing in my bank account. When will it come?"),
        ("Refund kab aayega", "mera refund abhi tak nahi aaya, return pickup 4 din pehle ho gaya tha. UPI se payment kiya tha"),
        ("Refund for COD order", "I paid cash on delivery and returned the item. How will I get my refund back?"),
        ("Partial refund", "I returned only 1 item out of 3 from my order. Will I get the delivery charge back too?"),
    ],
    "payment_issue": [
        ("Charged twice", "I was charged twice for the same order. Please refund the extra payment."),
        ("Payment failed but money deducted", "My UPI payment failed but money was debited from my account and no order was created."),
        ("Double payment!!!", "You took money TWICE from my card for one order!!! This is the second time I am writing. Fix it now."),
        ("Paise kat gaye", "payment fail ho gaya par mere paise kat gaye, order bhi nahi bana. kya karun?"),
        ("Payment pending", "My order shows payment pending for 1 hour but money is gone from my account."),
        ("COD limit", "Can I pay cash on delivery for an order of 12000 rupees?"),
    ],
    "delivery_delay": [
        ("Order not delivered", "My order was supposed to arrive yesterday but it is still not delivered. What should I do?"),
        ("Delivery delayed", "The estimated delivery date has passed 3 days ago and my parcel has not arrived yet."),
        ("Same day delivery", "Do you have same day delivery in Hyderabad and how much does it cost?"),
        ("Order kab aayega", "mera order 5 din se shipped dikha raha hai par abhi tak nahi aaya, kab aayega?"),
        ("Marked delivered not received", "My package is marked as delivered but I never received it."),
        ("Express delivery", "How fast is express delivery and is it free for Plus members?"),
    ],
    "account_login": [
        ("Forgot password", "I forgot my password and cannot log in. How do I reset it?"),
        ("Reset link expired", "The password reset link says it has expired. What should I do?"),
        ("Account locked", "My account got locked after entering the wrong password many times."),
        ("Password bhool gaya", "password bhool gaya hoon, account mein login kaise karun?"),
        ("Delete my account", "How can I permanently delete my ShopNest account?"),
        ("Change email", "I want to change the email address linked to my account."),
    ],
    "address_change": [
        ("Change delivery address", "I placed an order an hour ago, can I still change the delivery address?"),
        ("Wrong address", "I entered the wrong address and my order is already shipped. Can you change it?"),
        ("Add office address", "How do I add my office address as a second address?"),
        ("Address change karna hai", "order ka delivery address change karna hai, kaise karun?"),
        ("Address after packed", "My order status is packed. Is it too late to update the shipping address?"),
    ],
    "subscription": [
        ("Unsubscribe newsletter", "Please stop sending me promotional newsletter emails."),
        ("Cancel Plus membership", "I want to cancel my ShopNest Plus annual membership. Will I get a refund?"),
        ("Plus benefits", "What benefits do I get with ShopNest Plus?"),
        ("Early termination fee", "Is there an early termination fee if I cancel the Plus annual plan after 2 months?"),
        ("Stop emails", "I keep getting marketing emails, how do I unsubscribe?"),
    ],
    "gift_card": [   # NOT in the knowledge base on purpose -> knowledge gaps + human review
        ("Gift card redeem", "How do I redeem a ShopNest gift card that I received?"),
        ("Gift card balance", "How can I check the balance on my gift card?"),
        ("Gift card expired", "My gift card shows expired, can it be extended?"),
    ],
}


def _demo_user_ids(db) -> list[int]:
    # includes the customer used by scripts/agent_demo.py, so --reset removes everything demo-made
    emails = [e for _, e in CUSTOMERS] + ["demo.customer@shopnest.com"]
    return list(db.scalars(select(User.id).where(User.email.in_(emails))))


def reset(db) -> None:
    # gaps whose ticket no longer exists (left over from older demo runs)
    db.execute(delete(KnowledgeGap).where(KnowledgeGap.ticket_id.is_(None)))
    db.commit()
    ids = _demo_user_ids(db)
    if not ids:
        return
    ticket_ids = select(Ticket.id).where(Ticket.customer_id.in_(ids))
    db.execute(delete(KnowledgeGap).where(KnowledgeGap.ticket_id.in_(ticket_ids)))
    db.execute(delete(Feedback).where(Feedback.ticket_id.in_(ticket_ids)))
    n = db.execute(delete(Ticket).where(Ticket.customer_id.in_(ids))).rowcount
    db.commit()
    print(f"Removed {n} previous demo tickets")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=6.0, help="seconds between tickets (Groq rate limits)")
    parser.add_argument("--reset", action="store_true", help="delete previous demo data first")
    args = parser.parse_args()
    setup_logging("WARNING")
    rng = random.Random(42)

    with SessionLocal() as db:
        staff = db.scalar(select(User).where(User.role == UserRole.staff).order_by(User.id))
        if staff is None:
            raise SystemExit("Create a staff account first: python -m scripts.create_staff --name ... --email ...")
        if args.reset:
            reset(db)

        customers = []
        for name, email in CUSTOMERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(name=name, email=email, password_hash=hash_password(PASSWORD), role=UserRole.customer)
                db.add(user)
                db.commit()
            customers.append(user)

        all_tickets = [(theme, s, b) for theme, items in THEMES.items() for s, b in items]
        rng.shuffle(all_tickets)
        created: list[Ticket] = []
        t_start = time.time()
        for i, (theme, subject, body) in enumerate(all_tickets, start=1):
            ticket = Ticket(customer_id=rng.choice(customers).id, subject=subject, body=body, status=TicketStatus.open)
            db.add(ticket)
            db.commit()
            ticket = process_ticket(db, ticket)
            created.append(ticket)
            reasons = ", ".join(ticket.review_reasons or []) or "-"
            print(f"[{i:>2}/{len(all_tickets)}] {ticket.status.value:<15} conf={ticket.confidence!s:<6} "
                  f"{ticket.category or '?':<13} {subject[:35]:<35} {reasons[:60]}")
            if i < len(all_tickets):
                time.sleep(args.delay)

        # Staff reviews ~60% of pending tickets (approve the AI draft, or reject injections)
        pending = [t for t in created if t.status == TicketStatus.pending_review]
        reviewed = 0
        for t in pending:
            if rng.random() < 0.6:
                if t.ai_draft:
                    resume_ticket(db, t, "approve", None, staff)
                else:
                    resume_ticket(db, t, "edit", "Thanks for reaching out - our team has looked into this for you.", staff)
                reviewed += 1

        # Customers rate answered tickets: mostly 👍, ~12% 👎 (👎 on an AI answer escalates it)
        rated = escalated = 0
        for t in created:
            db.refresh(t)
            if t.status in (TicketStatus.ai_resolved, TicketStatus.agent_resolved) and rng.random() < 0.8:
                rating = -1 if rng.random() < 0.12 else 1
                db.add(Feedback(ticket_id=t.id, rating=rating))
                if rating == -1 and t.status == TicketStatus.ai_resolved:
                    t.status, t.priority, t.resolved_at = TicketStatus.pending_review, TicketPriority.high, None
                    t.review_reasons = [*(t.review_reasons or []), "customer_unhappy_with_ai_answer"]
                    escalated += 1
                rated += 1
        db.commit()

        by_status: dict[str, int] = {}
        for t in created:
            db.refresh(t)
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        print(f"\nDone in {time.time() - t_start:.0f}s: {len(created)} tickets {by_status}")
        print(f"Staff reviewed {reviewed} | feedback given {rated} | escalated by 👎 {escalated}")
        print("Now run: python -m scripts.analytics_demo")


if __name__ == "__main__":
    main()
