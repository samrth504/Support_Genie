"""Auth tests: signup, login, /me, roles and the security edge-cases."""
import jwt
from fastapi import Depends
from fastapi.testclient import TestClient

from app.core.security import require_role
from app.main import app
from app.models.user import User, UserRole
from tests.conftest import login

SIGNUP = {"name": "Rahul Verma", "email": "Rahul@Example.com", "password": "Password123"}


# A tiny staff-only route, only for testing require_role()
@app.get("/api/_test/staff-only")
def _staff_only(user: User = Depends(require_role(UserRole.staff))):
    return {"ok": True, "role": user.role.value}


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["database"] == "ok"
    assert "X-Request-ID" in resp.headers


def test_signup_creates_customer_and_returns_token(client: TestClient):
    resp = client.post("/api/auth/signup", json=SIGNUP)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "customer"          # public signup can never create staff
    assert body["user"]["email"] == "rahul@example.com"  # emails are normalised to lowercase
    assert "password" not in str(body) and "password_hash" not in str(body)


def test_signup_ignores_role_field(client: TestClient):
    resp = client.post("/api/auth/signup", json={**SIGNUP, "role": "staff"})
    assert resp.status_code == 201
    assert resp.json()["user"]["role"] == "customer"


def test_duplicate_email_rejected(client: TestClient):
    client.post("/api/auth/signup", json=SIGNUP)
    resp = client.post("/api/auth/signup", json={**SIGNUP, "email": "rahul@example.com"})
    assert resp.status_code == 409


def test_weak_password_rejected(client: TestClient):
    for bad in ["short1", "onlyletters", "12345678", "a1" * 40]:
        resp = client.post("/api/auth/signup", json={**SIGNUP, "password": bad})
        assert resp.status_code == 422, bad


def test_login_and_me(client: TestClient):
    client.post("/api/auth/signup", json=SIGNUP)
    token = login(client, "RAHUL@example.com", SIGNUP["password"])  # login is case-insensitive
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Rahul Verma"


def test_wrong_password_and_unknown_email_give_same_error(client: TestClient):
    client.post("/api/auth/signup", json=SIGNUP)
    wrong_pw = client.post("/api/auth/login", data={"username": SIGNUP["email"], "password": "Wrong12345"})
    no_user = client.post("/api/auth/login", data={"username": "nobody@example.com", "password": "Wrong12345"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_me_requires_valid_token(client: TestClient):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    forged = jwt.encode({"sub": "1", "role": "staff"}, "not-the-real-secret-but-long-enough-123", algorithm="HS256")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_role_protection(client: TestClient, staff_user: dict):
    client.post("/api/auth/signup", json=SIGNUP)
    customer_token = login(client, SIGNUP["email"], SIGNUP["password"])
    staff_token = login(client, staff_user["email"], staff_user["password"])

    assert client.get("/api/_test/staff-only", headers={"Authorization": f"Bearer {customer_token}"}).status_code == 403
    resp = client.get("/api/_test/staff-only", headers={"Authorization": f"Bearer {staff_token}"})
    assert resp.status_code == 200 and resp.json()["role"] == "staff"


# ---------------------------------------------------------------- change password
def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_change_password_flow(client: TestClient):
    client.post("/api/auth/signup", json=SIGNUP)
    token = login(client, SIGNUP["email"], SIGNUP["password"])
    url = "/api/auth/change-password"

    assert client.post(url, json={"current_password": "Wrong12345", "new_password": "NewPass456"},
                       headers=_headers(token)).status_code == 400            # wrong current password
    assert client.post(url, json={"current_password": SIGNUP["password"], "new_password": "short"},
                       headers=_headers(token)).status_code == 422            # weak new password
    assert client.post(url, json={"current_password": SIGNUP["password"], "new_password": SIGNUP["password"]},
                       headers=_headers(token)).status_code == 400            # same as old
    assert client.post(url, json={"current_password": SIGNUP["password"], "new_password": "NewPass456"}).status_code == 401
    assert client.post(url, json={"current_password": SIGNUP["password"], "new_password": "NewPass456"},
                       headers=_headers(token)).status_code == 204

    old = client.post("/api/auth/login", data={"username": SIGNUP["email"], "password": SIGNUP["password"]})
    assert old.status_code == 401                                             # old password no longer works
    assert login(client, SIGNUP["email"], "NewPass456")                       # new one does


# ---------------------------------------------------------------- rate limiting
def test_login_is_rate_limited(client: TestClient, monkeypatch):
    from app.core import rate_limit
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    rate_limit.login_limiter.reset()
    try:
        codes = [client.post("/api/auth/login", data={"username": "x@shopnest.com", "password": "Wrong12345"}).status_code
                 for _ in range(11)]
        assert codes[:10] == [401] * 10
        assert codes[10] == 429                                               # 11th attempt within a minute
        blocked = client.post("/api/auth/login", data={"username": "x@shopnest.com", "password": "Wrong12345"})
        assert "Retry-After" in blocked.headers
    finally:
        rate_limit.login_limiter.reset()


def test_rate_limit_cannot_be_bypassed_with_a_fake_forwarded_header(client: TestClient, monkeypatch):
    """Security regression: a client must not dodge the limiter by sending X-Forwarded-For itself."""
    from app.core import rate_limit
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    rate_limit.login_limiter.reset()
    try:
        codes = [client.post("/api/auth/login", data={"username": "x@shopnest.com", "password": "Wrong12345"},
                             headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(12)]
        assert 429 in codes, codes            # a new fake IP per request must NOT reset the counter
    finally:
        rate_limit.login_limiter.reset()


def test_client_ip_uses_the_entry_added_by_our_trusted_proxy(monkeypatch):
    from starlette.requests import Request

    from app.core.config import get_settings
    from app.core.rate_limit import client_ip

    def req(xff):
        headers = [(b"x-forwarded-for", xff.encode())] if xff else []
        return Request({"type": "http", "headers": headers, "client": ("10.1.1.1", 1234)})

    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 0)
    assert client_ip(req("1.2.3.4")) == "10.1.1.1"                    # no proxy: header ignored
    monkeypatch.setattr(get_settings(), "trusted_proxy_hops", 1)
    assert client_ip(req("6.6.6.6, 203.0.113.7")) == "203.0.113.7"    # spoofed prefix ignored
    assert client_ip(req("203.0.113.7")) == "203.0.113.7"
    assert client_ip(req("")) == "10.1.1.1"                            # header missing: fall back to peer
