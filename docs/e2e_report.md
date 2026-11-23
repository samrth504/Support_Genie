# SupportGenie - live end-to-end test report

Run `b21925` on 2026-11-21 19:18 UTC against `http://localhost:8001` (real Groq LLM, Neon Postgres + pgvector). Took 150 s.

**89 passed · 0 warnings · 0 failed** (89 checks)

WARN = depends on the LLM's wording or judgement, not a code bug.

| Area | Check | Result | Detail |
| --- | --- | --- | --- |
| health | /health status ok + database ok | PASS |  |
| auth | signup -> 201 | PASS |  |
| auth | signup ignores role:'staff' (always customer) | PASS |  |
| auth | email stored lowercase | PASS |  |
| auth | password never returned | PASS |  |
| auth | duplicate email -> 409 | PASS |  |
| auth | weak password (no digit) -> 422 | PASS |  |
| auth | wrong password -> 401 | PASS |  |
| auth | unknown email gives the SAME error (no email leak) | PASS |  |
| auth | login -> token | PASS |  |
| auth | /me returns the logged-in user | PASS |  |
| auth | /me without token -> 401 | PASS |  |
| auth | /me with garbage token -> 401 | PASS |  |
| auth | change password with wrong current -> 400 | PASS |  |
| auth | change password -> 204 | PASS |  |
| auth | login works with the NEW password | PASS |  |
| auth | staff login -> role staff | PASS |  |
| permissions | customer -> /api/review/queue = 403 | PASS |  |
| permissions | customer -> /api/kb/documents = 403 | PASS |  |
| permissions | customer -> /api/analytics/summary = 403 | PASS |  |
| permissions | customer -> /api/analytics/trends = 403 | PASS |  |
| permissions | customer -> /api/analytics/gaps = 403 | PASS |  |
| permissions | staff cannot raise a ticket (403) | PASS |  |
| permissions | no token -> /api/tickets = 401 | PASS |  |
| validation | too-short ticket -> 422 (no LLM call) | PASS |  |
| validation | subject > 200 chars -> 422 | PASS |  |
| agent | create 'Forgot my password' -> 201 (5.7s) | PASS |  |
| agent | create 'Same-day delivery' -> 201 (12.6s) | PASS |  |
| agent | create 'Payment methods' -> 201 (7.4s) | PASS |  |
| agent | create 'Refund kitne din mein' -> 201 (7.0s) | PASS |  |
| agent | create 'Charged twice' -> 201 (7.1s) | PASS |  |
| agent | create 'THIRD time writing!!!' -> 201 (7.1s) | PASS |  |
| agent | create 'Gift card' -> 201 (7.2s) | PASS |  |
| agent | create 'Card problem' -> 201 (7.1s) | PASS |  |
| agent | create 'Special request' -> 201 (4.2s) | PASS |  |
| agent | 'password' auto-resolved by AI | PASS |  |
| agent | 'password' reply + sources shown to customer | PASS |  |
| agent | 'delivery' auto-resolved by AI | PASS |  |
| agent | 'delivery' reply + sources shown to customer | PASS |  |
| agent | 'methods' auto-resolved by AI | PASS |  |
| agent | 'methods' reply + sources shown to customer | PASS |  |
| agent | classifier: password ticket = ACCOUNT | PASS |  |
| agent | RAG grounded: delivery reply mentions the ₹149 fee | PASS |  |
| agent | Hinglish ticket detected as hinglish | PASS |  |
| agent | Hinglish ticket has a draft/reply | PASS |  |
| agent | 'charged twice' -> pending_review | PASS |  |
| agent | 'charged twice' reason money_problem_needs_human | PASS |  |
| agent | 'charged twice' priority HIGH | PASS |  |
| agent | angry customer -> pending_review | PASS |  |
| agent | angry customer detected as frustrated | PASS |  |
| agent | gift card -> pending_review | PASS |  |
| agent | gift card reason answer_not_in_knowledge_base | PASS |  |
| safety | PII: card + phone masked for staff view | PASS |  |
| safety | PII: AI draft never contains the card / phone | PASS |  |
| safety | injection -> pending_review, flag set | PASS |  |
| safety | injection -> LLM never called (no draft) | PASS |  |
| safety | injection -> priority HIGH | PASS |  |
| safety | customer view of pending ticket: no reply, no draft, no confidence | PASS |  |
| permissions | another customer opening my ticket -> 404 | PASS |  |
| permissions | another customer's list does not show my tickets | PASS |  |
| tickets | customer list shows all 9 tickets, newest first | PASS |  |
| review | every pending test ticket is in the queue | PASS |  |
| review | queue sorted by priority (high first) | PASS |  |
| review | approve -> agent_resolved (LangGraph resumed) | PASS |  |
| review | customer now sees the approved reply (answered_by=agent) | PASS |  |
| review | reviewing an already-resolved ticket -> 409 | PASS |  |
| review | edit without a reply -> 422 | PASS |  |
| review | edit -> customer gets the edited text | PASS |  |
| review | approve with NO draft -> 422 (must write a reply) | PASS |  |
| review | reject -> rejected + standard message to customer | PASS |  |
| feedback | 👍 on AI answer -> saved | PASS |  |
| feedback | second feedback -> 409 | PASS |  |
| feedback | 👎 on AI answer -> escalated to human, HIGH | PASS |  |
| feedback | feedback on an unanswered ticket -> 409 | PASS |  |
| feedback | rating other than ±1 -> 422 | PASS |  |
| kb | upload .md -> 202 processing | PASS |  |
| kb | background indexing -> ready with chunks | PASS |  |
| kb | new doc is found by semantic search (top result) | PASS |  |
| kb | same filename again -> 409 | PASS |  |
| kb | unsupported type (.png) -> 422 | PASS |  |
| kb | file over 2 MB -> 413 | PASS |  |
| kb | delete doc -> 204 | PASS |  |
| kb | deleted doc no longer searchable | PASS |  |
| analytics | summary has all KPI fields | PASS |  |
| analytics | total_tickets counts our 9 tickets | PASS |  |
| analytics | 14 days in tickets_per_day, today > 0 | PASS |  |
| analytics | trends: clusters (K in 4-8) or an explanation | PASS |  |
| analytics | gift-card question logged as a knowledge gap | PASS |  |
| security | brute-force login gets 429 within 12 tries | PASS |  |
