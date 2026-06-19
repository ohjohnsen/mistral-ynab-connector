"""MCP Server implementation for YNAB Connector.

This module provides the FastAPI-based MCP server that exposes
YNAB functionality to the Model Context Protocol.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query

from config import settings
from ynab_client import YNABClient

# Global YNAB client instance (for backward compatibility with env var)
_ynab_client: YNABClient | None = None


def get_ynab_api_key(
    authorization: str | None = Header(default=None),
) -> str:
    """Extract YNAB API key from Authorization header or settings.
    
    Supports MCP authentication via Bearer token in Authorization header.
    Falls back to YNAB_API_KEY environment variable.
    """
    if authorization:
        # Extract token from "Bearer <token>" header
        if authorization.startswith("Bearer "):
            return authorization[7:]
        return authorization
    
    if settings.ynab_api_key:
        return settings.ynab_api_key
    
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide YNAB_API_KEY via Authorization header or environment variable.",
    )


def get_ynab_client(
    api_key: str = Depends(get_ynab_api_key),
) -> YNABClient:
    """Get or create the YNAB client instance with the provided API key."""
    global _ynab_client
    
    # If we have a header-based API key, create a new client for this request
    # This allows different MCP clients to use different YNAB tokens
    if api_key != settings.ynab_api_key:
        return YNABClient(api_key=api_key)
    
    # Otherwise use the global client (for env var based auth)
    if _ynab_client is None:
        if not settings.ynab_api_key:
            raise HTTPException(
                status_code=400,
                detail="YNAB_API_KEY not configured. Please set it in your environment.",
            )
        _ynab_client = YNABClient()
    return _ynab_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    global _ynab_client
    if settings.ynab_api_key:
        _ynab_client = YNABClient()
    yield
    # Shutdown
    if _ynab_client:
        await _ynab_client.close()


# Create FastAPI application
app = FastAPI(
    title=settings.mcp_name,
    version=settings.mcp_version,
    description="YNAB MCP Connector - Interact with You Need A Budget API",
    lifespan=lifespan,
)


# MCP Standard Endpoints


@app.get("/mcp/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for MCP."""
    return {"status": "healthy", "version": settings.mcp_version}


@app.get("/mcp/info")
async def mcp_info() -> dict[str, Any]:
    """Get MCP server information."""
    return {
        "name": settings.mcp_name,
        "version": settings.mcp_version,
        "description": "YNAB API Connector",
        "capabilities": {
            "budgets": {"read": True},
            "categories": {"read": True},
            "accounts": {"read": True},
            "transactions": {"read": True, "write": True},
        },
    }


# YNAB API Endpoints


@app.get("/api/budgets")
async def list_budgets(
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """List all accessible YNAB budgets."""
    return await client.get_budgets()


@app.get("/api/budgets/{budget_id}")
async def get_budget(
    budget_id: str,
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """Get details for a specific budget."""
    return await client.get_budget(budget_id)


@app.get("/api/budgets/{budget_id}/categories")
async def list_categories(
    budget_id: str,
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """List all categories for a budget."""
    return await client.get_categories(budget_id)


@app.get("/api/budgets/{budget_id}/accounts")
async def list_accounts(
    budget_id: str,
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """List all accounts for a budget."""
    return await client.get_accounts(budget_id)


@app.get("/api/budgets/{budget_id}/transactions")
async def list_transactions(
    budget_id: str,
    account_id: str | None = Query(default=None, description="Filter by account ID"),
    since_date: str | None = Query(default=None, description="Get transactions since date (YYYY-MM-DD)"),
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """List transactions for a budget, optionally filtered by account and date."""
    return await client.get_transactions(budget_id, account_id, since_date)


@app.post("/api/budgets/{budget_id}/transactions")
async def create_transaction(
    budget_id: str,
    transaction: dict[str, Any],
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """Create a new transaction.

    The transaction should follow the YNAB API format:
    {
        "account_id": "...",
        "date": "2024-01-01",
        "amount": 100000,
        "payee_id": "...",
        "payee_name": "...",
        "category_id": "...",
        "memo": "...",
        "cleared": "cleared|uncleared|reconciled",
        "approved": true,
        "flag_color": "red|orange|yellow|green|blue|purple"
    }
    """
    return await client.create_transaction(budget_id, transaction)


# MCP Resource Endpoints (for resource access)


@app.get("/mcp/resources/budgets")
async def mcp_list_budgets(
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """MCP endpoint to list budgets as resources."""
    budgets = await client.get_budgets()
    return {
        "resources": [
            {
                "uri": f"ynab://budget/{budget['id']}",
                "name": budget["name"],
                "type": "budget",
                "budget": budget,
            }
            for budget in budgets.get("data", {}).get("budgets", [])
        ]
    }


@app.get("/mcp/resources/budgets/{budget_id}/accounts")
async def mcp_list_accounts(
    budget_id: str,
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """MCP endpoint to list accounts as resources."""
    accounts = await client.get_accounts(budget_id)
    return {
        "resources": [
            {
                "uri": f"ynab://account/{account['id']}",
                "name": account["name"],
                "type": "account",
                "account": account,
            }
            for account in accounts.get("data", {}).get("accounts", [])
        ]
    }


@app.get("/mcp/resources/budgets/{budget_id}/categories")
async def mcp_list_categories(
    budget_id: str,
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """MCP endpoint to list categories as resources."""
    categories = await client.get_categories(budget_id)
    return {
        "resources": [
            {
                "uri": f"ynab://category/{category['id']}",
                "name": category["name"],
                "type": "category",
                "category": category,
            }
            for category in categories.get("data", {}).get("category_groups", [])
            for category in category.get("categories", [])
        ]
    }


# MCP Tool Endpoints


@app.post("/mcp/tools/get_budget")
async def mcp_get_budget_tool(
    body: dict[str, Any],
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """MCP tool to get budget details."""
    budget_id = body.get("budget_id")
    if not budget_id:
        raise HTTPException(status_code=400, detail="budget_id is required")
    budget = await client.get_budget(budget_id)
    return {"content": [{"type": "text", "text": str(budget)}]}


@app.post("/mcp/tools/get_transactions")
async def mcp_get_transactions_tool(
    body: dict[str, Any],
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """MCP tool to get transactions."""
    budget_id = body.get("budget_id")
    account_id = body.get("account_id")
    since_date = body.get("since_date")
    if not budget_id:
        raise HTTPException(status_code=400, detail="budget_id is required")
    transactions = await client.get_transactions(budget_id, account_id, since_date)
    return {"content": [{"type": "text", "text": str(transactions)}]}


@app.post("/mcp/tools/create_transaction")
async def mcp_create_transaction_tool(
    body: dict[str, Any],
    client: YNABClient = Depends(get_ynab_client),
) -> dict[str, Any]:
    """MCP tool to create a transaction."""
    budget_id = body.get("budget_id")
    transaction_data = body.get("transaction")
    if not budget_id:
        raise HTTPException(status_code=400, detail="budget_id is required")
    if not transaction_data:
        raise HTTPException(status_code=400, detail="transaction data is required")
    result = await client.create_transaction(budget_id, transaction_data)
    return {"content": [{"type": "text", "text": f"Created transaction: {result}"}]}
