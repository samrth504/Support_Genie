"""Test setup: a throw-away SQLite database, so tests never touch the real Neon DB."""
import os
import tempfile
from pathlib import Path

# Must be set BEFORE the app is imported (settings + engine are created at import time)
_TEST_DB = Path(tempfile.gettempdir()) / "supportgenie_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-1234567890"
os.environ["ENVIRONMENT"] = "test"
os.environ["PRELOAD_MODELS"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"   # tests log in many times; the limiter has its own test
# Tests must never call real LLM providers (or spend free-tier quota), even if .env has keys
os.environ["GROQ_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Every test starts with empty tables."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def staff_user() -> dict:
    creds = {"email": "amit@shopnest.com", "password": "StaffPass123"}
    with SessionLocal() as db:
        db.add(User(name="Amit", email=creds["email"], password_hash=hash_password(creds["password"]),
                    role=UserRole.staff))
        db.commit()
    return creds


def login(client: TestClient, email: str, password: str) -> str:
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
