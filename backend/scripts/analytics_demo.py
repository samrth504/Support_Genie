"""Print the dashboard analytics straight from the database (no login needed).

    python -m scripts.analytics_demo
"""
import json

from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.services import analytics


def main() -> None:
    setup_logging("WARNING")
    with SessionLocal() as db:
        s = analytics.summary(db)
        print("=== SUMMARY ===")
        for key in ("total_tickets", "auto_resolution_rate", "pending_review", "avg_confidence",
                    "avg_ai_response_seconds", "avg_agent_response_seconds", "knowledge_gaps"):
            print(f"{key:<28} {s[key]}")
        print(f"{'by_status':<28} {s['by_status']}")
        print(f"{'feedback':<28} {s['feedback']}")
        print(f"{'by_category':<28} {s['by_category']}")
        print(f"{'knowledge_base':<28} {s['knowledge_base']}")

        t = analytics.trends(db)
        print(f"\n=== TRENDS (K-means) === tickets={t['tickets_analysed']} k={t['k']} silhouette={t['silhouette']}")
        if t.get("message"):
            print(t["message"])
        for c in t["clusters"]:
            print(f"- {c['label']:<35} size={c['size']:<3} top_category={c['top_category']:<10} "
                  f"keywords={c['keywords']}  examples={c['examples']}")

        print("\n=== KNOWLEDGE GAPS ===")
        print(json.dumps(analytics.knowledge_gaps(db, 10), indent=2, default=str))


if __name__ == "__main__":
    main()
