"""Database engine, session factory and the FastAPI session dependency."""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Parent class of every SQLAlchemy model (Alembic reads Base.metadata)."""


def _build_engine():
    url = get_settings().database_url
    if url.startswith("sqlite"):
        # Used by the test-suite only. SQLite ignores foreign keys unless told otherwise.
        eng = create_engine(url, connect_args={"check_same_thread": False})

        @event.listens_for(eng, "connect")
        def _enable_fk(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        return eng
    return create_engine(
        url,
        pool_pre_ping=True,   # Neon scales to zero -> check a connection is alive before using it
        pool_recycle=300,     # drop connections older than 5 minutes
        pool_size=5,
        max_overflow=5,
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """One DB session per request, always closed afterwards (even on errors)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
