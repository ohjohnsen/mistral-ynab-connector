"""MCP Server implementation for YNAB Connector.

This module provides the FastAPI-based MCP server that exposes
YNAB functionality to the Model Context Protocol using JSON-RPC 2.0.

All endpoints use the official YNAB API v1.85.0 terminology (/plans/ not /budgets/).
"""

from contextlib import asynccontextmanager
from datetime import datetime
import json
import re
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from config import settings
from ynab_client import YNABClient

# Global YNAB client instance
_ynab_client: YNABClient | None = None


# ============================================================================
# Validation Helpers
# ============================================================================

def _validate_date_format(date_str: str | None, param_name: str) -> str | None:
    """Validate that a date string is in YYYY-MM-DD format.
    
    Args:
        date_str: The date string to validate
        param_name: Name of the parameter for error messages
        
    Returns:
        The validated date string, or None if not provided
        
    Raises:
        ValueError: If the date format is invalid
    """
    if date_str is None:
        return None
    
    if not isinstance(date_str, str):
        raise ValueError(f"{param_name} must be a string in YYYY-MM-DD format, got {type(date_str).__name__}")
    
    # YNAB expects YYYY-MM-DD format
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError(f"{param_name} must be in YYYY-MM-DD format, got: {date_str}")
    
    # Optional: Validate it's a real date
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{param_name} is not a valid date: {date_str}")
    
    return date_str


def _validate_required_param(param: Any, param_name: str, expected_type: type | tuple = str) -> Any:
    """Validate that a required parameter is provided and of the correct type.
    
    Args:
        param: The parameter value
        param_name: Name of the parameter for error messages
        expected_type: Expected type(s) of the parameter
        
    Returns:
        The validated parameter value
        
    Raises:
        ValueError: If the parameter is missing or of wrong type
    """
    if param is None:
        raise ValueError(f"{param_name} is required")
    
    if not isinstance(param, expected_type):
        raise ValueError(f"{param_name} must be of type {expected_type.__name__ if isinstance(expected_type, type) else expected_type}, got {type(param).__name__}")
    
    return param


def get_ynab_api_key(
    authorization: str | None = Header(default=None),
) -> str:
    """Extract YNAB API key from Authorization header or settings.
    
    Supports MCP authentication via Bearer token in Authorization header.
    Falls back to YNAB_API_KEY environment variable.
    """
    if authorization:
        if authorization.startswith("Bearer "):
            return authorization[7:]
        return authorization
    
    if settings.ynab_api_key:
        return settings.ynab_api_key
    
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide YNAB API key as Bearer token in Authorization header or set YNAB_API_KEY environment variable.",
    )


def get_ynab_client(
    api_key: str = Depends(get_ynab_api_key),
) -> YNABClient:
    """Get or create the YNAB client instance with the provided API key."""
    global _ynab_client
    
    # If we have a header-based API key, create a new client for this request
    if api_key != settings.ynab_api_key:
        return YNABClient(api_key=api_key)
    
    # Use the global client for env var based auth
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
    global _ynab_client
    if settings.ynab_api_key:
        _ynab_client = YNABClient()
    yield
    if _ynab_client:
        _ynab_client.close()


# Create FastAPI application
app = FastAPI(
    title=settings.mcp_name,
    version=settings.mcp_version,
    description="YNAB MCP Connector - Interact with You Need A Budget API v1",
    lifespan=lifespan,
)


# ============================================================================
# MCP Server Discovery Endpoint
# ============================================================================

@app.get("/.well-known/mcp/server-card")
async def server_card() -> dict[str, Any]:
    """MCP Server Card for discovery.
    
    Allows MCP clients to discover the server.
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
                "write": {},
            },
        },
        "hints": {
            "resourceTemplates": [
                {
                    "uriTemplate": "ynab://user",
                    "name": "YNAB User",
                    "description": "Authenticated user information",
                },
                {
                    "uriTemplate": "ynab://plans",
                    "name": "All Plans",
                    "description": "List all YNAB plans",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}",
                    "name": "Plan",
                    "description": "A specific YNAB plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/settings",
                    "name": "Plan Settings",
                    "description": "Settings for a specific plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/accounts",
                    "name": "Plan Accounts",
                    "description": "All accounts for a plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/accounts/{account_id}",
                    "name": "Account",
                    "description": "A specific account",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/categories",
                    "name": "Plan Categories",
                    "description": "All categories for a plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/categories/{category_id}",
                    "name": "Category",
                    "description": "A specific category",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/payees",
                    "name": "Plan Payees",
                    "description": "All payees for a plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/payees/{payee_id}",
                    "name": "Payee",
                    "description": "A specific payee",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/months",
                    "name": "Plan Months",
                    "description": "All months for a plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/months/{month}",
                    "name": "Plan Month",
                    "description": "A specific month for a plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/transactions",
                    "name": "Plan Transactions",
                    "description": "All transactions for a plan",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/transactions/{transaction_id}",
                    "name": "Transaction",
                    "description": "A specific transaction",
                },
                {
                    "uriTemplate": "ynab://plan/{plan_id}/scheduled_transactions",
                    "name": "Scheduled Transactions",
                    "description": "All scheduled transactions for a plan",
                },
            ]
        },
    }


# ============================================================================
# MCP JSON-RPC 2.0 Protocol Endpoint
# ============================================================================

MCP_PROTOCOL_VERSION = "2024-11-05"


@app.post("/mcp")
async def mcp_handler(request: Request) -> JSONResponse:
    """Handle MCP JSON-RPC 2.0 requests.
    
    Implements the Model Context Protocol specification.
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
        elif method == "resources/write":
            result = await _handle_resources_write(params, request_id)
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
                    "write": {
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "uri": {"type": "string"},
                                "content": {"type": "string"},
                            },
                            "required": ["uri", "content"],
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
        # User tools
        {
            "name": "get_user",
            "description": "Get authenticated YNAB user information",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        # Plans tools
        {
            "name": "get_plans",
            "description": "Get all plans accessible with the API key",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "include_accounts": {
                        "type": "boolean",
                        "description": "Whether to include plan accounts",
                        "default": False,
                    },
                },
            },
        },
        {
            "name": "get_plan",
            "description": "Get a specific plan by ID with all related entities",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan ID (can be 'last-used' or 'default')",
                    },
                    "last_knowledge_of_server": {
                        "type": "integer",
                        "description": "Starting server knowledge for delta request",
                    },
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_plan_settings",
            "description": "Get settings for a specific plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "string",
                        "description": "The plan ID (can be 'last-used' or 'default')",
                    },
                },
                "required": ["plan_id"],
            },
        },
        # Accounts tools
        {
            "name": "get_accounts",
            "description": "Get all accounts for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "last_knowledge_of_server": {"type": "integer"},
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_account",
            "description": "Get a specific account by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "account_id": {"type": "string", "description": "The account ID (UUID)"},
                },
                "required": ["plan_id", "account_id"],
            },
        },
        {
            "name": "create_account",
            "description": "Create a new account",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "account": {
                        "type": "object",
                        "description": "Account data with name, type, and balance (milliunits)",
                        "required": ["name", "type", "balance"],
                    },
                },
                "required": ["plan_id", "account"],
            },
        },
        # Categories tools
        {
            "name": "get_categories",
            "description": "Get all categories for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "last_knowledge_of_server": {"type": "integer"},
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_category",
            "description": "Get a specific category by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "category_id": {"type": "string", "description": "The category ID"},
                },
                "required": ["plan_id", "category_id"],
            },
        },
        {
            "name": "create_category",
            "description": "Create a new category",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "category": {
                        "type": "object",
                        "description": "Category data including name and category_group_id",
                        "required": ["name", "category_group_id"],
                    },
                },
                "required": ["plan_id", "category"],
            },
        },
        {
            "name": "update_category",
            "description": "Update an existing category",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "category_id": {"type": "string", "description": "The category ID"},
                    "category": {"type": "object", "description": "Category data to update"},
                },
                "required": ["plan_id", "category_id", "category"],
            },
        },
        # Payees tools
        {
            "name": "get_payees",
            "description": "Get all payees for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "last_knowledge_of_server": {"type": "integer"},
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_payee",
            "description": "Get a specific payee by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "payee_id": {"type": "string", "description": "The payee ID"},
                },
                "required": ["plan_id", "payee_id"],
            },
        },
        {
            "name": "create_payee",
            "description": "Create a new payee",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "payee": {"type": "object", "description": "Payee data with name"},
                },
                "required": ["plan_id", "payee"],
            },
        },
        # Months tools
        {
            "name": "get_months",
            "description": "Get all months for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "last_knowledge_of_server": {"type": "integer"},
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_month",
            "description": "Get a specific month for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "month": {
                        "type": "string",
                        "description": "Month in ISO format (YYYY-MM-DD) or 'current'",
                    },
                },
                "required": ["plan_id", "month"],
            },
        },
        # Transactions tools
        {
            "name": "get_transactions",
            "description": "Get transactions for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "since_date": {"type": "string", "description": "Transactions on or after this date (YYYY-MM-DD)"},
                    "until_date": {"type": "string", "description": "Transactions on or before this date (YYYY-MM-DD)"},
                    "type": {
                        "type": "string",
                        "enum": ["uncategorized", "unapproved"],
                        "description": "Filter by transaction type",
                    },
                    "last_knowledge_of_server": {"type": "integer"},
                    "limit": {"type": "integer", "description": "Maximum number of transactions to return (client-side pagination)", "minimum": 1},
                    "offset": {"type": "integer", "description": "Number of transactions to skip (client-side pagination)", "minimum": 0, "default": 0},
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_transaction",
            "description": "Get a specific transaction by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "transaction_id": {"type": "string", "description": "The transaction ID"},
                },
                "required": ["plan_id", "transaction_id"],
            },
        },
        {
            "name": "create_transaction",
            "description": "Create a new transaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "transaction": {
                        "type": "object",
                        "description": "Single transaction data",
                    },
                    "transactions": {
                        "type": "array",
                        "description": "Multiple transactions data",
                        "items": {"type": "object"},
                    },
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "update_transaction",
            "description": "Update a single transaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "transaction_id": {"type": "string", "description": "The transaction ID"},
                    "transaction": {"type": "object", "description": "Transaction data to update"},
                },
                "required": ["plan_id", "transaction_id", "transaction"],
            },
        },
        {
            "name": "update_transactions",
            "description": "Update multiple transactions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "transactions": {
                        "type": "array",
                        "description": "List of transactions to update (each with id or import_id)",
                        "items": {"type": "object"},
                    },
                },
                "required": ["plan_id", "transactions"],
            },
        },
        {
            "name": "delete_transaction",
            "description": "Delete a transaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "transaction_id": {"type": "string", "description": "The transaction ID"},
                },
                "required": ["plan_id", "transaction_id"],
            },
        },
        {
            "name": "import_transactions",
            "description": "Import transactions from linked accounts",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                },
                "required": ["plan_id"],
            },
        },
        # Scheduled Transactions tools
        {
            "name": "get_scheduled_transactions",
            "description": "Get all scheduled transactions for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "last_knowledge_of_server": {"type": "integer"},
                },
                "required": ["plan_id"],
            },
        },
        {
            "name": "get_scheduled_transaction",
            "description": "Get a specific scheduled transaction by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "scheduled_transaction_id": {"type": "string", "description": "The scheduled transaction ID"},
                },
                "required": ["plan_id", "scheduled_transaction_id"],
            },
        },
        {
            "name": "create_scheduled_transaction",
            "description": "Create a new scheduled transaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "scheduled_transaction": {"type": "object", "description": "Scheduled transaction data"},
                },
                "required": ["plan_id", "scheduled_transaction"],
            },
        },
        {
            "name": "update_scheduled_transaction",
            "description": "Update a scheduled transaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "scheduled_transaction_id": {"type": "string", "description": "The scheduled transaction ID"},
                    "scheduled_transaction": {"type": "object", "description": "Scheduled transaction data to update"},
                },
                "required": ["plan_id", "scheduled_transaction_id", "scheduled_transaction"],
            },
        },
        {
            "name": "delete_scheduled_transaction",
            "description": "Delete a scheduled transaction",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string", "description": "The plan ID"},
                    "scheduled_transaction_id": {"type": "string", "description": "The scheduled transaction ID"},
                },
                "required": ["plan_id", "scheduled_transaction_id"],
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
        # User tools
        if name == "get_user":
            data = await client.get_user()
            content = [{"type": "text", "text": json.dumps(data)}]
        
        # Plans tools
        elif name == "get_plans":
            include_accounts = arguments.get("include_accounts", False)
            data = await client.get_plans(include_accounts=include_accounts)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_plan":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_plan(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_plan_settings":
            plan_id = arguments.get("plan_id")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_plan_settings(plan_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        # Accounts tools
        elif name == "get_accounts":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_accounts(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_account":
            plan_id = arguments.get("plan_id")
            account_id = arguments.get("account_id")
            if not plan_id or not account_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and account_id are required"}, "id": request_id}
            data = await client.get_account(plan_id, account_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "create_account":
            plan_id = arguments.get("plan_id")
            account_data = arguments.get("account")
            if not plan_id or not account_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and account are required"}, "id": request_id}
            data = await client.create_account(plan_id, account_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        # Categories tools
        elif name == "get_categories":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_categories(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_category":
            plan_id = arguments.get("plan_id")
            category_id = arguments.get("category_id")
            if not plan_id or not category_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and category_id are required"}, "id": request_id}
            data = await client.get_category(plan_id, category_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "create_category":
            plan_id = arguments.get("plan_id")
            category_data = arguments.get("category")
            if not plan_id or not category_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and category are required"}, "id": request_id}
            data = await client.create_category(plan_id, category_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "update_category":
            plan_id = arguments.get("plan_id")
            category_id = arguments.get("category_id")
            category_data = arguments.get("category")
            if not plan_id or not category_id or not category_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id, category_id, and category are required"}, "id": request_id}
            data = await client.update_category(plan_id, category_id, category_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        # Payees tools
        elif name == "get_payees":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_payees(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_payee":
            plan_id = arguments.get("plan_id")
            payee_id = arguments.get("payee_id")
            if not plan_id or not payee_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and payee_id are required"}, "id": request_id}
            data = await client.get_payee(plan_id, payee_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "create_payee":
            plan_id = arguments.get("plan_id")
            payee_data = arguments.get("payee")
            if not plan_id or not payee_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and payee are required"}, "id": request_id}
            data = await client.create_payee(plan_id, payee_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        # Months tools
        elif name == "get_months":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_months(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_month":
            plan_id = arguments.get("plan_id")
            month = arguments.get("month")
            if not plan_id or not month:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and month are required"}, "id": request_id}
            data = await client.get_month(plan_id, month)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        # Transactions tools
        elif name == "get_transactions":
            plan_id = arguments.get("plan_id")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            
            try:
                # Validate required parameters
                _validate_required_param(plan_id, "plan_id", str)
                
                # Validate date formats
                since_date = _validate_date_format(arguments.get("since_date"), "since_date")
                until_date = _validate_date_format(arguments.get("until_date"), "until_date")
                
                type_filter = arguments.get("type")
                last_knowledge = arguments.get("last_knowledge_of_server")
                
                # Pagination parameters (client-side, default to no limit)
                limit = arguments.get("limit")
                offset = arguments.get("offset", 0)
                
                if limit is not None:
                    try:
                        limit = int(limit)
                        if limit <= 0:
                            raise ValueError("limit must be a positive integer")
                    except (ValueError, TypeError):
                        raise ValueError("limit must be a positive integer")
                
                if offset is not None:
                    try:
                        offset = int(offset)
                        if offset < 0:
                            raise ValueError("offset must be a non-negative integer")
                    except (ValueError, TypeError):
                        raise ValueError("offset must be a non-negative integer")
                
                data = await client.get_transactions(
                    plan_id,
                    since_date=since_date,
                    until_date=until_date,
                    type_filter=type_filter,
                    last_knowledge_of_server=last_knowledge,
                )
                
                # Apply client-side pagination if limit is specified
                if limit is not None and "data" in data and "transactions" in data["data"]:
                    transactions = data["data"]["transactions"]
                    paginated = transactions[offset:offset + limit]
                    data["data"]["transactions"] = paginated
                    # Add pagination metadata
                    data["data"]["pagination"] = {
                        "limit": limit,
                        "offset": offset,
                        "total": len(transactions)
                    }
                
                content = [{"type": "text", "text": json.dumps(data)}]
            except ValueError as e:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": str(e)}, "id": request_id}
        
        elif name == "get_transaction":
            plan_id = arguments.get("plan_id")
            transaction_id = arguments.get("transaction_id")
            if not plan_id or not transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and transaction_id are required"}, "id": request_id}
            data = await client.get_transaction(plan_id, transaction_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "create_transaction":
            plan_id = arguments.get("plan_id")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            transaction_data = arguments.get("transaction") or arguments.get("transactions", {})
            data = await client.create_transaction(plan_id, transaction_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "update_transaction":
            plan_id = arguments.get("plan_id")
            transaction_id = arguments.get("transaction_id")
            transaction_data = arguments.get("transaction")
            if not plan_id or not transaction_id or not transaction_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id, transaction_id, and transaction are required"}, "id": request_id}
            data = await client.update_transaction(plan_id, transaction_id, transaction_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "update_transactions":
            plan_id = arguments.get("plan_id")
            transactions = arguments.get("transactions")
            if not plan_id or not transactions:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and transactions are required"}, "id": request_id}
            data = await client.update_transactions(plan_id, transactions)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "delete_transaction":
            plan_id = arguments.get("plan_id")
            transaction_id = arguments.get("transaction_id")
            if not plan_id or not transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and transaction_id are required"}, "id": request_id}
            data = await client.delete_transaction(plan_id, transaction_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "import_transactions":
            plan_id = arguments.get("plan_id")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.import_transactions(plan_id)
            content = [{"type": "text", "text": f"Imported transactions: {data}"}]
        
        # Scheduled Transactions tools
        elif name == "get_scheduled_transactions":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_scheduled_transactions(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "get_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            scheduled_transaction_id = arguments.get("scheduled_transaction_id")
            if not plan_id or not scheduled_transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and scheduled_transaction_id are required"}, "id": request_id}
            data = await client.get_scheduled_transaction(plan_id, scheduled_transaction_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "create_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            transaction_data = arguments.get("scheduled_transaction")
            if not plan_id or not transaction_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and scheduled_transaction are required"}, "id": request_id}
            data = await client.create_scheduled_transaction(plan_id, transaction_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "update_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            scheduled_transaction_id = arguments.get("scheduled_transaction_id")
            transaction_data = arguments.get("scheduled_transaction")
            if not plan_id or not scheduled_transaction_id or not transaction_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id, scheduled_transaction_id, and scheduled_transaction are required"}, "id": request_id}
            data = await client.update_scheduled_transaction(plan_id, scheduled_transaction_id, transaction_data)
            content = [{"type": "text", "text": json.dumps(data)}]
        
        elif name == "delete_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            scheduled_transaction_id = arguments.get("scheduled_transaction_id")
            if not plan_id or not scheduled_transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and scheduled_transaction_id are required"}, "id": request_id}
            data = await client.delete_scheduled_transaction(plan_id, scheduled_transaction_id)
            content = [{"type": "text", "text": json.dumps(data)}]
        
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
    """Handle MCP resources/list request.
    
    Lists available YNAB resources that can be read.
    """
    client = YNABClient(api_key=settings.ynab_api_key)
    
    try:
        resources = []
        
        # Add user resource
        resources.append({
            "uri": "ynab://user",
            "name": "YNAB User",
            "description": "Authenticated user information",
            "mimeType": "application/json",
        })
        
        # Get all plans and add resources for each
        plans_response = await client.get_plans()
        plans = plans_response.get("data", {}).get("plans", [])
        
        for plan in plans:
            plan_id = plan.get("id", "")
            plan_name = plan.get("name", "Unknown Plan")
            
            # Plan resource
            resources.append({
                "uri": f"ynab://plan/{plan_id}",
                "name": f"Plan: {plan_name}",
                "description": f"YNAB Plan - {plan_name}",
                "mimeType": "application/json",
            })
            
            # Plan settings
            resources.append({
                "uri": f"ynab://plan/{plan_id}/settings",
                "name": f"Settings: {plan_name}",
                "description": f"Settings for plan: {plan_name}",
                "mimeType": "application/json",
            })
            
            # Accounts
            resources.append({
                "uri": f"ynab://plan/{plan_id}/accounts",
                "name": f"Accounts: {plan_name}",
                "description": f"Accounts for plan: {plan_name}",
                "mimeType": "application/json",
            })
            
            # Categories
            resources.append({
                "uri": f"ynab://plan/{plan_id}/categories",
                "name": f"Categories: {plan_name}",
                "description": f"Categories for plan: {plan_name}",
                "mimeType": "application/json",
            })
            
            # Payees
            resources.append({
                "uri": f"ynab://plan/{plan_id}/payees",
                "name": f"Payees: {plan_name}",
                "description": f"Payees for plan: {plan_name}",
                "mimeType": "application/json",
            })
            
            # Months
            resources.append({
                "uri": f"ynab://plan/{plan_id}/months",
                "name": f"Months: {plan_name}",
                "description": f"Months for plan: {plan_name}",
                "mimeType": "application/json",
            })
            
            # Transactions
            resources.append({
                "uri": f"ynab://plan/{plan_id}/transactions",
                "name": f"Transactions: {plan_name}",
                "description": f"Transactions for plan: {plan_name}",
                "mimeType": "application/json",
            })
            
            # Scheduled Transactions
            resources.append({
                "uri": f"ynab://plan/{plan_id}/scheduled_transactions",
                "name": f"Scheduled Transactions: {plan_name}",
                "description": f"Scheduled transactions for plan: {plan_name}",
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
    """Handle MCP resources/read request.
    
    Read data from a YNAB resource URI.
    """
    uri = params.get("uri")
    
    if not uri:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "uri is required"},
            "id": request_id,
        }
    
    client = YNABClient(api_key=settings.ynab_api_key)
    
    try:
        # Parse the URI and fetch data
        if uri == "ynab://user":
            data = await client.get_user()
        
        elif uri.startswith("ynab://plan/"):
            parts = uri.replace("ynab://plan/", "").split("/")
            plan_id = parts[0]
            
            if len(parts) == 1:
                # Get full plan
                data = await client.get_plan(plan_id)
            elif parts[1] == "settings":
                data = await client.get_plan_settings(plan_id)
            elif parts[1] == "accounts":
                data = await client.get_accounts(plan_id)
            elif parts[1] == "categories":
                data = await client.get_categories(plan_id)
            elif parts[1] == "payees":
                data = await client.get_payees(plan_id)
            elif parts[1] == "months":
                if len(parts) == 2:
                    data = await client.get_months(plan_id)
                else:
                    month = parts[2]
                    data = await client.get_month(plan_id, month)
            elif parts[1] == "transactions":
                if len(parts) == 2:
                    data = await client.get_transactions(plan_id)
                else:
                    transaction_id = parts[2]
                    data = await client.get_transaction(plan_id, transaction_id)
            elif parts[1] == "scheduled_transactions":
                if len(parts) == 2:
                    data = await client.get_scheduled_transactions(plan_id)
                else:
                    scheduled_transaction_id = parts[2]
                    data = await client.get_scheduled_transaction(plan_id, scheduled_transaction_id)
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": f"Unsupported URI: {uri}"},
                    "id": request_id,
                }
        
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
                    "text": json.dumps(data),
                }
            ],
            "id": request_id,
        }
    
    finally:
        client.close()


async def _handle_resources_write(
    params: dict[str, Any], request_id: Any
) -> dict[str, Any]:
    """Handle MCP resources/write request.
    
    Write data to a YNAB resource URI (for create/update operations).
    """
    uri = params.get("uri")
    content = params.get("content")
    
    if not uri:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "uri is required"},
            "id": request_id,
        }
    
    if not content:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "content is required"},
            "id": request_id,
        }
    
    client = YNABClient(api_key=settings.ynab_api_key)
    
    try:
        import json
        data = json.loads(content)
        
        # Parse the URI and perform write operation
        if uri.startswith("ynab://plan/"):
            parts = uri.replace("ynab://plan/", "").split("/")
            plan_id = parts[0]
            
            if len(parts) >= 2:
                resource_type = parts[1]
                
                if resource_type == "accounts" and len(parts) == 2:
                    # Create account
                    result = await client.create_account(plan_id, data)
                elif resource_type == "categories" and len(parts) == 2:
                    # Create category
                    result = await client.create_category(plan_id, data.get("category", data))
                elif resource_type == "payees" and len(parts) == 2:
                    # Create payee
                    result = await client.create_payee(plan_id, data.get("payee", data))
                elif resource_type == "transactions" and len(parts) == 2:
                    # Create transaction(s)
                    result = await client.create_transaction(plan_id, data)
                elif resource_type == "scheduled_transactions" and len(parts) == 2:
                    # Create scheduled transaction
                    result = await client.create_scheduled_transaction(plan_id, data.get("scheduled_transaction", data))
                elif resource_type == "categories" and len(parts) == 3:
                    # Update category
                    category_id = parts[2]
                    result = await client.update_category(plan_id, category_id, data.get("category", data))
                elif resource_type == "transactions" and len(parts) == 3:
                    # Update transaction
                    transaction_id = parts[2]
                    result = await client.update_transaction(plan_id, transaction_id, data.get("transaction", data))
                elif resource_type == "scheduled_transactions" and len(parts) == 3:
                    # Update scheduled transaction
                    scheduled_transaction_id = parts[2]
                    result = await client.update_scheduled_transaction(plan_id, scheduled_transaction_id, data.get("scheduled_transaction", data))
                else:
                    return {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": f"Write not supported for URI: {uri}"},
                        "id": request_id,
                    }
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32602, "message": f"Write not supported for URI: {uri}"},
                    "id": request_id,
                }
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Write not supported for URI: {uri}"},
                "id": request_id,
            }
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "uri": uri,
                "text": str(result),
            },
            "id": request_id,
        }
    
    except json.JSONDecodeError:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid JSON in content"},
            "id": request_id,
        }
    
    finally:
        client.close()


# ============================================================================
# REST API Endpoints (for direct HTTP access)
# ============================================================================

@app.get("/mcp/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.mcp_version}


@app.get("/mcp/info")
async def mcp_info() -> dict[str, Any]:
    """Get MCP server information."""
    return {
        "name": settings.mcp_name,
        "version": settings.mcp_version,
        "description": "YNAB API Connector aligned with official OpenAPI spec",
        "api_version": "1.85.0",
        "base_url": settings.ynab_api_url,
        "capabilities": {
            "user": {"read": True},
            "plans": {"read": True},
            "accounts": {"read": True, "write": True},
            "categories": {"read": True, "write": True},
            "payees": {"read": True, "write": True},
            "months": {"read": True},
            "transactions": {"read": True, "write": True, "delete": True},
            "scheduled_transactions": {"read": True, "write": True, "delete": True},
            "money_movements": {"read": True},
        },
    }
