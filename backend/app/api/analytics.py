"""Staff analytics dashboard endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_role
from app.models.user import User, UserRole
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics (staff)"])
staff_only = require_role(UserRole.staff)


@router.get("/summary")
def get_summary(days: int = Query(default=14, ge=1, le=90), db: Session = Depends(get_db), _: User = Depends(staff_only)) -> dict:
    """KPIs: auto-resolution rate, satisfaction, response times, tickets by category/day..."""
    return analytics.summary(db, days)


@router.get("/trends")
def get_trends(days: int = Query(default=30, ge=1, le=180), db: Session = Depends(get_db), _: User = Depends(staff_only)) -> dict:
    """Trending issues: K-means clusters of recent tickets (K chosen by silhouette score)."""
    return analytics.trends(db, days)


@router.get("/gaps")
def get_gaps(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), _: User = Depends(staff_only)) -> list[dict]:
    """Questions the knowledge base could not answer -> which help docs to write next."""
    return analytics.knowledge_gaps(db, limit)
