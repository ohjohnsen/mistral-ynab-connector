"""MCP Server implementation for YNAB Connector.

This module provides the FastAPI-based MCP server that exposes
YNAB functionality to the Model Context Protocol using JSON-RPC 2.0.
"""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

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
        _ynab_client.close()


# Create FastAPI application
app = FastAPI(
    title=settings.mcp_name,
    version=settings.mcp_version,
    description="YNAB MCP Connector - Interact with You Need A Budget API",
    lifespan=lifespan,
)


# ============================================================================
# MCP Server Discovery Endpoint
# ============================================================================

@app.get("/.well-known/mcp/server-card/mcp")
async def server_card() -> dict[str, Any]:
    """MCP Server Card for discovery.
    
    This endpoint allows MCP clients to discover the server.
    https://github.com/modelcontextprotocol/specification/blob/main/specification/Server%20Card.md
    """
    return {
        "name": settings.mcp_name,
        "description": "YNAB MCP Connector - Interact with You Need A Budget API",
        "version": settings.mcp_version,
        "url": "/mcp",
        "auth": {
            "type": "api_key",
            "headerName": "Authorization",
            "description": "Provide YNAB API key as Bearer token",
        },
        "capabilities": {
            "tools": {},
            "resources": {
                "list": {},
                "read": {},
            },
        },
    }


# ============================================================================
# MCP JSON-RPC 2.0 Protocol Endpoint
# ============================================================================

MCP_PROTOCOL_VERSION = "2024-11-05"


@app.post("/mcp")
async def mcp_handler(request: Request) -> JSONResponse:
    """Handle MCP JSON-RPC 2.0 requests.
    
    This endpoint implements the Model Context Protocol specification.
    https://github.com/modelcontextprotocol/specification
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Invalid JSON",
                },
                "id": None,
            },
        )
    
    # Handle batch requests
    if isinstance(body, list):
        results = []
        for req in body:
            result = await _handle_rpc_request(req)
            results.append(result)
        return JSONResponse(content=results)
    
    # Handle single request
    result = await _handle_rpc_request(body)
    return JSONResponse(content=result)


async def _handle_rpc_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a single JSON-RPC 2.0 request."""
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})
    
    try:
        if method == "initialize":
            result = await _handle_initialize(params, request_id)
        elif method == "tools/list":
            result = await _handle_tools_list(params, request_id)
        elif method == "tools/call":
            result = await _handle_tools_call(params, request_id)
        elif method == "resources/list":
            result = await _handle_resources_list(params, request_id)
        elif method == "resources/read":
            result = await _handle_resources_read(params, request_id)
        else:
            result = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
                "id": request_id,
            }
        
        return result
    
    except HTTPException as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32000,
                "message": e.detail,
            },
            "id": request_id,
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e),
            },
            "id": request_id,
        }


async def _handle_initialize(
    params: dict[str, Any], request_id: Any
) -> dict[str, Any]:
    """Handle MCP initialize request."""
    client_info = params.get("clientInfo", {})
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {},
                "resources": {
                    "list": {},
                    "read": {
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "uri": {"type": "string"},
                            },
                            "required": ["uri"],
                        }
                    },
                },
            },
            "serverInfo": {
                "name": settings.mcp_name,
                "version": settings.mcp_version,
            },
        },
        "id": request_id,
    }


async def _handle_tools_list(
    params: dict[str, Any], request_id: Any
) -> dict[str, Any]:
    """Handle MCP tools/list request."""
    tools = [
        {
            "name": "get_budget",
            "description": "Get details for a specific YNAB budget",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "budget_id": {
                        "type": "string",
                        "description": "The YNAB budget ID",
                    },
                },
                "required": ["budget_id"],
            },
        },
        {
            "name": "get_transactions",
            "description": "Get transactions for a budget, optionally filtered",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "budget_id": {"type": "string", "description": "The YNAB budget ID"},
                    "account_id": {"type": "string", "description": "Optional account ID filter"},
                    "since_date": {"type": "string", "description": "Get transactions since date (YYYY-MM-DD)"},
                },
                "required": ["budget_id"],
            },
        },
        {
            "name": "create_transaction",
            "description": "Create a new transaction in YNAB",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "budget_id": {"type": "string", "description": "The YNAB budget ID"},
                    "transaction": {
                        "type": "object",
                        "description": "Transaction data following YNAB API format",
                    },
                },
                "required": ["budget_id", "transaction"],
            },
        },
    ]
    
    return {
        "jsonrpc": "2.0",
        "result": {
            "tools": tools,
        },
        "id": request_id,
    }


async def _handle_tools_call(
    params: dict[str, Any], request_id: Any
) -> dict[str, Any]:
    """Handle MCP tools/call request."""
    name = params.get("name")
    arguments = params.get("arguments", {})
    
    client = YNABClient(api_key=settings.ynab_api_key)
    
    try:
        if name == "get_budget":
            budget_id = arguments.get("budget_id")
            if not budget_id:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "budget_id is required"},
                    "id": request_id,
                }
            budget = await client.get_budget(budget_id)
            content = [{"type": "text", "text": str(budget)}]
        
        elif name == "get_transactions":
            budget_id = arguments.get("budget_id")
            account_id = arguments.get("account_id")
            since_date = arguments.get("since_date")
            if not budget_id:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "budget_id is required"},
                    "id": request_id,
                }
            transactions = await client.get_transactions(budget_id, account_id, since_date)
            content = [{"type": "text", "text": str(transactions)}]
        
        elif name == "create_transaction":
            budget_id = arguments.get("budget_id")
            transaction_data = arguments.get("transaction")
            if not budget_id:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "budget_id is required"},
                    "id": request_id,
                }
            if not transaction_data:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": "transaction data is required"},
                    "id": request_id,
                }
            result = await client.create_transaction(budget_id, transaction_data)
            content = [{"type": "text", "text": f"Created transaction: {result}"}]
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Tool not found: {name}"},
                "id": request_id,
            }
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": content,
            },
            "id": request_id,
        }
    
    finally:
        client.close()


async def _handle_resources_list(
    params: dict[str, Any], request_id: Any
) -> dict[str, Any]:
    """Handle MCP resources/list request."""
    client = YNABClient(api_key=settings.ynab_api_key)
    
    try:
        budgets = await client.get_budgets()
        
        resources = []
        for budget in budgets.get("data", {}).get("budgets", []):
            resources.append({
                "uri": f"ynab://budget/{budget['id']}",
                "name": budget.get("name", "Unknown Budget"),
                "description": f"YNAB Budget: {budget.get('name', '')}",
                "mimeType": "application/json",
            })
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "resources": resources,
            },
            "id": request_id,
        }
    
    finally:
        client.close()


async def _handle_resources_read(
    params: dict[str, Any], request_id: Any
) -> dict[str, Any]:
    """Handle MCP resources/read request."""
    uri = params.get("uri")
    
    if not uri:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "uri is required"},
            "id": request_id,
        }
    
    client = YNABClient(api_key=settings.ynab_api_key)
    
    try:
        # Parse the URI
        if uri.startswith("ynab://budget/"):
            budget_id = uri.replace("ynab://budget/", "")
            data = await client.get_budget(budget_id)
        elif uri.startswith("ynab://account/"):
            # Accounts need budget context, but we'll just return the URI for now
            data = {"uri": uri, "type": "account"}
        elif uri.startswith("ynab://category/"):
            data = {"uri": uri, "type": "category"}
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Unsupported URI: {uri}"},
                "id": request_id,
            }
        
        return {
            "jsonrpc": "2.0",
            "result": [
                {
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": str(data),
                }
            ],
            "id": request_id,
        }
    
    finally:
        client.close()


# ============================================================================
# REST API Endpoints (for backward compatibility)
# ============================================================================

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


# YNAB API Endpoints (REST)


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
