# SupportGenie MCP server

Exposes **read-only** SupportGenie tools to any MCP client (Claude Desktop, MCP Inspector, IDEs):

| Tool | What it does |
|---|---|
| `search_knowledge_base(query, k)` | Semantic search over the ShopNest help docs |
| `list_pending_reviews(limit)` | Tickets waiting for a human, most urgent first, with escalation reasons |
| `get_ticket(ticket_id)` | One ticket: masked message, category, AI draft, confidence, sources |
| `get_support_stats(days)` | KPIs: auto-resolution rate, satisfaction, response times |
| `get_trending_issues(days)` | K-means clusters of recent tickets |
| `get_knowledge_gaps(limit)` | Questions the docs could not answer |

**Design:** the server calls the SupportGenie REST API as a *staff* user — it never touches the
database directly, so authentication, role checks and PII masking still apply. It only exposes
GET endpoints (no approve/reject), so an AI client cannot change any data.

## Setup

```
# from the project root, with the venv active
pip install -r mcp_server/requirements.txt
```

The backend must be running (`uvicorn app.main:app` in `backend/`).

## Connect to Claude Desktop

Claude Desktop → Settings → Developer → **Edit Config**, then add (adjust paths/credentials):

```json
{
  "mcpServers": {
    "supportgenie": {
      "command": "D:\\Capstone project\\.venv\\Scripts\\python.exe",
      "args": ["D:\\Capstone project\\mcp_server\\server.py"],
      "env": {
        "SUPPORTGENIE_API_URL": "http://localhost:8000",
        "SUPPORTGENIE_EMAIL": "amit@shopnest.com",
        "SUPPORTGENIE_PASSWORD": "your-staff-password"
      }
    }
  }
}
```

Restart Claude Desktop, then ask for example:
- *"Use SupportGenie to show me the tickets waiting for review."*
- *"What does our knowledge base say about Cash on Delivery limits?"*
- *"What are the trending issues this month?"*

## Test without Claude Desktop (MCP Inspector)

```
npx @modelcontextprotocol/inspector "D:\Capstone project\.venv\Scripts\python.exe" "D:\Capstone project\mcp_server\server.py"
```
(set the three `SUPPORTGENIE_*` variables in the Inspector's environment panel)
