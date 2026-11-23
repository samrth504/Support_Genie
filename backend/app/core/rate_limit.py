"""Simple sliding-window rate limiter (in memory, per process).

Protects:
  * login / signup   -> password guessing and fake-account spam
  * ticket creation  -> each ticket costs an LLM call; this protects the free Groq quota

In-memory is fine for one server instance (Render free tier = 1 instance). With several
instances you would move the counters to Redis.

Usage:  @router.post("/login", dependencies=[Depends(RateLimiter("login", 10, 60))])
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    """The IP we rate-limit on - built so a client CANNOT fake it.

    X-Forwarded-For looks like "fake1, fake2, <ip seen by proxy 1>, <ip seen by proxy 2>": every proxy
    APPENDS the address it received the request from, and anything to the left may have been typed
    by the client. So we never read the first entry. Instead:
      * TRUSTED_PROXY_HOPS = 0 (local development, no proxy) -> ignore the header completely
      * TRUSTED_PROXY_HOPS = N (N proxies we control in front, e.g. 1 on Render) -> take the N-th
        entry from the RIGHT, i.e. the address our outermost trusted proxy actually saw
    (Found in testing: trusting the first entry let a client bypass the limiter with a fake header.)
    """
    peer = request.client.host if request.client else "unknown"
    hops = get_settings().trusted_proxy_hops
    if hops <= 0:
        return peer
    chain = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return chain[-hops] if len(chain) >= hops else peer


class RateLimiter:
    def __init__(self, scope: str, max_calls: int, window_seconds: int):
        self.scope = scope
        self.max_calls = max_calls
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def __call__(self, request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        client = client_ip(request)
        now = time.monotonic()
        with self._lock:
            hits = self._hits[client]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.max_calls:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please wait {retry_after} seconds and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


login_limiter = RateLimiter("login", max_calls=10, window_seconds=60)
signup_limiter = RateLimiter("signup", max_calls=5, window_seconds=60)
ticket_limiter = RateLimiter("tickets", max_calls=20, window_seconds=60)
