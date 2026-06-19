"""Main entry point for the YNAB MCP Connector."""

import uvicorn

from config import settings
from mcp_server import app


def main() -> None:
    """Run the YNAB MCP Connector server."""
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
        reload=True,
        reload_excludes=["tests/*"],
    )


if __name__ == "__main__":
    main()
