"""FastAPI application factory.

Run locally (from the backend/ folder):
    uvicorn app.main:app --reload --no-proxy-headers
Then open http://localhost:8000/docs
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analytics, auth, health, kb, review, tickets
from app.core.config import get_settings
from app.core.logging import setup_logging

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting %s v%s (%s)", settings.app_name, settings.version, settings.environment)
    # Heavy models are loaded ONCE per process here, so no request pays the loading cost.
    agent = None
    if settings.preload_models:
        from app.agent.graph import get_agent
        from app.services.ml.classifier import get_classifier
        from app.services.rag.embeddings import get_embedder

        get_embedder()
        get_classifier()
        agent = get_agent()   # also creates the LangGraph checkpoint tables on first run
    yield
    # close the checkpointer's connection pool cleanly
    pool = getattr(getattr(agent, "checkpointer", None), "conn", None)
    if pool is not None and hasattr(pool, "close"):
        pool.close()
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="AI customer-support copilot: ML classification + RAG + LangGraph human-in-the-loop.",
        lifespan=lifespan,
        # Hide interactive docs in production
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """Gives every request an ID + logs method, path, status and duration."""
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error | id=%s %s %s", request_id, request.method, request.url.path)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info("%s %s -> %s (%.0f ms) id=%s", request.method, request.url.path,
                    response.status_code, duration_ms, request_id)
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(kb.router)
    app.include_router(tickets.router)
    app.include_router(review.router)
    app.include_router(analytics.router)
    return app


app = create_app()
