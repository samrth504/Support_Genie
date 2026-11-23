# ShopNest Help Center — demo knowledge base

**ShopNest is a fictional Indian e-commerce company created for this capstone project.**
All policies, prices, phone numbers and email addresses in these documents are made up.

These Markdown files are the knowledge base for the RAG pipeline. Each file maps to one
or more categories the ML classifier predicts:

| File | Classifier category |
|---|---|
| account.md | ACCOUNT |
| orders.md | ORDER |
| cancellation.md | CANCEL |
| refunds_returns.md | REFUND |
| payments.md | PAYMENT |
| invoices.md | INVOICE |
| delivery.md | DELIVERY |
| shipping_address.md | SHIPPING |
| subscription.md | SUBSCRIPTION |
| contact_support.md | CONTACT |
| feedback_complaints.md | FEEDBACK |

**Intentionally NOT covered** (to demo "knowledge gaps" + human escalation):
gift cards, international shipping, product warranty / repairs, bulk / B2B orders.

Load all of them into the database with (from `backend/`):

```
python -m scripts.seed_kb
```
