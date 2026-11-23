"""Health check: used by the frontend's "server waking up" loader and by Render."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 - health check must never crash
        logger.exception("Database health check failed")
        db_status = "error"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": settings.version,
        "environment": settings.environment,
    }
