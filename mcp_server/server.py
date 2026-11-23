"""SupportGenie MCP server.

MCP (Model Context Protocol) is a standard way for AI apps (Claude Desktop, IDEs, agents) to use
external tools. This server exposes READ-ONLY SupportGenie tools, so a support agent can ask
Claude things like "show me today's urgent tickets" or "what does our refund policy say?".

It talks to the SupportGenie REST API (it never touches the database directly), logging in as
a STAFF user, so all the normal auth / role checks still apply.

Config (environment variables):
    SUPPORTGENIE_API_URL   default http://localhost:8000
    SUPPORTGENIE_EMAIL     staff email
    SUPPORTGENIE_PASSWORD  staff password

Run manually (for testing):  python mcp_server/server.py
"""
import os
import time

import httpx
# mcp >= 2.0 renamed FastMCP -> MCPServer (module mcp.server.fastmcp now only raises an error).
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

API_URL = os.environ.get("SUPPORTGENIE_API_URL", "http://localhost:8000").rstrip("/")
EMAIL = os.environ.get("SUPPORTGENIE_EMAIL", "")
PASSWORD = os.environ.get("SUPPORTGENIE_PASSWORD", "")

mcp = MCPServer("SupportGenie")
_token: dict = {"value": None, "expires_at": 0.0}


class SupportGenieError(ToolError):
    """Expected failure (bad login, API down, API error). In mcp 2.x only ToolError messages are
    sent to the client; any other exception is hidden behind a generic "Error executing tool"."""


def _login() -> str:
    if not EMAIL or not PASSWORD:
        raise SupportGenieError("Set SUPPORTGENIE_EMAIL and SUPPORTGENIE_PASSWORD for a staff account.")
    resp = httpx.post(f"{API_URL}/api/auth/login", data={"username": EMAIL, "password": PASSWORD}, timeout=60)
    if resp.status_code != 200:
        raise SupportGenieError(f"Login failed ({resp.status_code}): {resp.text[:200]}")
    body = resp.json()
    if body["user"]["role"] != "staff":
        raise SupportGenieError("The MCP server needs a STAFF account.")
    _token["value"] = body["access_token"]
    _token["expires_at"] = time.time() + body["expires_in"] - 60
    return _token["value"]


def _get(path: str, params: dict | None = None):
    """GET with automatic login + one retry if the token expired."""
    for attempt in range(2):
        token = _token["value"] if time.time() < _token["expires_at"] else _login()
        try:
            resp = httpx.get(f"{API_URL}{path}", params=params, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        except httpx.ConnectError:
            raise SupportGenieError(f"Cannot reach the SupportGenie API at {API_URL}. Is the backend running?")
        if resp.status_code == 401 and attempt == 0:
            _token["expires_at"] = 0
            continue
        if resp.status_code >= 400:
            raise SupportGenieError(f"API error {resp.status_code}: {resp.text[:300]}")
        return resp.json()
    raise SupportGenieError("Authentication failed")


def _short_ticket(t: dict) -> dict:
    return {k: t.get(k) for k in ("id", "subject", "status", "priority", "category", "confidence",
                                  "review_reasons", "customer_name", "created_at")}


# ------------------------------------------------------------------ tools
@mcp.tool()
def search_knowledge_base(query: str, k: int = 3) -> list[dict]:
    """Search ShopNest's help-center knowledge base (semantic search). Returns the most relevant
    passages with their document title, section and similarity score (0-1)."""
    return _get("/api/kb/search", {"q": query, "k": max(1, min(k, 10))})["results"]


@mcp.tool()
def list_pending_reviews(limit: int = 10) -> list[dict]:
    """List support tickets waiting for a human agent, most urgent first, with the reasons
    the AI escalated them (e.g. frustrated_customer, needs_account_action)."""
    return [_short_ticket(t) for t in _get("/api/review/queue")[: max(1, min(limit, 50))]]


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Full details of one ticket: customer message (PII-masked), predicted category, AI draft reply,
    confidence, sources used and current status."""
    t = _get(f"/api/review/tickets/{ticket_id}")
    t.pop("body", None)  # only expose the PII-masked text to the AI client
    return t


@mcp.tool()
def get_support_stats(days: int = 14) -> dict:
    """Support KPIs: total tickets, auto-resolution rate, customer satisfaction, average response
    times, tickets per category and per day."""
    return _get("/api/analytics/summary", {"days": days})


@mcp.tool()
def get_trending_issues(days: int = 30) -> dict:
    """Trending customer issues found by K-means clustering of recent tickets."""
    data = _get("/api/analytics/trends", {"days": days})
    for c in data.get("clusters", []):
        c.pop("ticket_ids", None)
    return data


@mcp.tool()
def get_knowledge_gaps(limit: int = 20) -> list[dict]:
    """Customer questions the knowledge base could NOT answer - tells you which help docs to write next."""
    return _get("/api/analytics/gaps", {"limit": limit})


if __name__ == "__main__":
    mcp.run()  # stdio transport (what Claude Desktop uses)
