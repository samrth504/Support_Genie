"""End-to-end check of the MCP server WITHOUT Claude Desktop.

Starts server.py as a real MCP stdio server, connects with the official MCP client,
lists the tools and calls three of them.

    # backend must be running; set staff credentials first (PowerShell):
    $env:SUPPORTGENIE_EMAIL="amit@shopnest.com"; $env:SUPPORTGENIE_PASSWORD="..."
    python mcp_server/smoke_test.py
"""
import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("server.py")


async def main() -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", ", ".join(t.name for t in tools.tools))

            for name, args in [
                ("search_knowledge_base", {"query": "cash on delivery limit", "k": 2}),
                ("list_pending_reviews", {"limit": 3}),
                ("get_support_stats", {"days": 7}),
            ]:
                result = await session.call_tool(name, args)
                text = "\n".join(c.text for c in result.content if hasattr(c, "text"))
                status = "ERROR" if result.is_error else "OK"   # mcp 2.x: snake_case field ("isError" is only the JSON alias)
                print(f"\n=== {name} [{status}] ===\n{text[:800]}")


if __name__ == "__main__":
    asyncio.run(main())
