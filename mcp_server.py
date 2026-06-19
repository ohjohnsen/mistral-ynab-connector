"""MCP Server implementation for YNAB Connector.

This module provides the FastAPI-based MCP server that exposes
YNAB functionality to the Model Context Protocol using JSON-RPC 2.0.

All endpoints use the official YNAB API v1.85.0 terminology (/plans/ not /budgets/).
"""

from __future__ import annotations

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
    
    # ==========================================================================
    # Schema Definitions for Tool Input/Output Types
    # ==========================================================================
    
    # Account Schema
    account_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the account"},
            "name": {"type": "string", "description": "Name of the account"},
            "type": {
                "type": "string",
                "enum": ["CHECKING", "SAVINGS", "CASH", "CREDIT_CARD", "LINE_OF_CREDIT", "OTHER_ASSET", "OTHER_LIABILITY"],
                "description": "Type of account"
            },
            "balance": {
                "type": "integer",
                "description": "Current balance in milliunits (1/1000 of currency unit)",
                "examples": [100000]
            },
            "cleared_balance": {
                "type": "integer",
                "description": "Cleared balance in milliunits"
            },
            "uncleared_balance": {
                "type": "integer",
                "description": "Uncleared balance in milliunits"
            },
            "closed": {"type": "boolean", "description": "Whether the account is closed"},
            "note": {"type": "string", "description": "Optional note for the account"},
            "on_budget": {"type": "boolean", "description": "Whether the account is on budget"},
        },
        "required": ["name", "type", "balance"],
    }
    
    # Category Schema
    category_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the category"},
            "name": {"type": "string", "description": "Name of the category"},
            "hidden": {"type": "boolean", "description": "Whether the category is hidden"},
            "original_category_group_id": {
                "type": "string",
                "description": "ID of the original category group"
            },
            "note": {"type": "string", "description": "Optional note for the category"},
        },
        "required": ["name"],
    }
    
    # Category Group Schema
    category_group_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the category group"},
            "name": {"type": "string", "description": "Name of the category group"},
            "hidden": {"type": "boolean", "description": "Whether the category group is hidden"},
            "categories": {
                "type": "array",
                "items": category_schema,
                "description": "List of categories in this group"
            },
        },
        "required": ["name"],
    }
    
    # Transaction Schema
    transaction_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the transaction"},
            "date": {
                "type": "string",
                "format": "date",
                "description": "Transaction date in YYYY-MM-DD format",
                "examples": ["2024-01-15"]
            },
            "amount": {
                "type": "integer",
                "description": "Transaction amount in milliunits (positive for inflow, negative for outflow)",
                "examples": [100000, -50000]
            },
            "memo": {"type": "string", "description": "Memo or description for the transaction"},
            "cleared": {
                "type": "string",
                "enum": ["cleared", "uncleared", "reconciled"],
                "description": "Cleared status of the transaction"
            },
            "approved": {"type": "boolean", "description": "Whether the transaction is approved"},
            "flag_color": {
                "type": "string",
                "enum": ["red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "grey", "black"],
                "description": "Color flag for the transaction"
            },
            "account_id": {"type": "string", "description": "ID of the account the transaction belongs to"},
            "payee_id": {"type": "string", "description": "ID of the payee (if linked)"},
            "payee_name": {"type": "string", "description": "Name of the payee"},
            "category_id": {"type": "string", "description": "ID of the category"},
            "category_name": {"type": "string", "description": "Name of the category"},
            "subtransactions": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of subtransactions (for split transactions)"
            },
            "transaction_type": {
                "type": "string",
                "description": "Type of transaction"
            },
            "import_id": {"type": "string", "description": "Import ID for imported transactions"},
        },
        "required": ["date", "amount"],
    }
    
    # Scheduled Transaction Schema
    scheduled_transaction_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the scheduled transaction"},
            "date_first": {
                "type": "string",
                "format": "date",
                "description": "First date of the scheduled transaction in YYYY-MM-DD format",
                "examples": ["2024-01-15"]
            },
            "date_next": {
                "type": "string",
                "format": "date",
                "description": "Next occurrence date in YYYY-MM-DD format"
            },
            "frequency": {
                "type": "string",
                "enum": ["daily", "weekly", "everyOtherWeek", "twiceAMonth", "every4Weeks", "monthly", "everyOtherMonth", "every3Months", "every6Months", "yearly", "everyOtherYear", "never"],
                "description": "How often the transaction occurs"
            },
            "amount": {
                "type": "integer",
                "description": "Amount in milliunits",
                "examples": [100000]
            },
            "memo": {"type": "string", "description": "Memo or description"},
            "flag_color": {
                "type": "string",
                "enum": ["red", "orange", "yellow", "green", "blue", "purple", "pink", "brown", "grey", "black"],
                "description": "Color flag"
            },
            "account_id": {"type": "string", "description": "ID of the account"},
            "payee_id": {"type": "string", "description": "ID of the payee"},
            "category_id": {"type": "string", "description": "ID of the category"},
            "category_name": {"type": "string", "description": "Name of the category"},
            "subtransactions": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of subtransactions"
            },
            "weeks_offset": {"type": "integer", "description": "Week offset for frequency"},
            "days_offset": {"type": "integer", "description": "Day offset for frequency"},
        },
        "required": ["date_first", "frequency", "amount"],
    }
    
    # Payee Schema
    payee_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the payee"},
            "name": {"type": "string", "description": "Name of the payee"},
            "transfer_account_id": {
                "type": "string",
                "description": "Account ID if this is a transfer payee"
            },
            "deleted": {"type": "boolean", "description": "Whether the payee is deleted"},
        },
        "required": ["name"],
    }
    
    # Plan Schema (simplified for input)
    plan_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Unique identifier for the plan"},
            "name": {"type": "string", "description": "Name of the plan"},
        },
    }
    
    # Month Schema
    month_schema = {
        "type": "object",
        "properties": {
            "month": {
                "type": "string",
                "format": "date",
                "description": "Month identifier in YYYY-MM-DD format",
                "examples": ["2024-01-01"]
            },
            "note": {"type": "string", "description": "Optional note for the month"},
            "to_be_budgeted": {
                "type": "integer",
                "description": "Amount to be budgeted in milliunits"
            },
            "age_of_money": {
                "type": "integer",
                "description": "Age of money in days"
            },
            "categories": {
                "type": "array",
                "items": {"type": "object"},
                "description": "List of category budget information for the month"
            },
        },
        "required": ["month"],
    }
    
    # Common parameter descriptions
    common_params = {
        "plan_id": {
            "type": "string",
            "description": "The plan ID (can be a UUID, 'last-used', or 'default')",
            "examples": ["d95502e5-1217-4a6c-935b-c053888b3497", "last-used"]
        },
        "last_knowledge_of_server": {
            "type": "integer",
            "description": "Starting server knowledge timestamp for delta/incremental updates. Used to fetch only changes since this timestamp.",
            "minimum": 0,
            "examples": [0]
        },
        "since_date": {
            "type": "string",
            "format": "date",
            "description": "Filter transactions on or after this date (YYYY-MM-DD format)",
            "examples": ["2024-01-01"]
        },
        "until_date": {
            "type": "string",
            "format": "date",
            "description": "Filter transactions on or before this date (YYYY-MM-DD format)",
            "examples": ["2024-12-31"]
        },
    }
    
    tools = [
        # User tools
        {
            "name": "get_user",
            "description": "Get authenticated YNAB user information",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "description": "No parameters required",
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "user": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Unique user identifier"},
                                    "email": {"type": "string", "description": "User's email address"},
                                },
                                "required": ["id"],
                            }
                        },
                        "required": ["user"],
                    }
                },
                "required": ["data"],
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
                        "description": "Whether to include the list of plan accounts in the response",
                        "default": False,
                    },
                },
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "plans": {
                                "type": "array",
                                "items": plan_schema,
                                "description": "List of all accessible plans"
                            }
                        },
                        "required": ["plans"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_plan",
            "description": "Get a specific plan by ID with all related entities",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "plan": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Plan identifier"},
                                    "name": {"type": "string", "description": "Plan name"},
                                    "accounts": {"type": "array", "items": account_schema},
                                    "categories": {"type": "array", "items": category_group_schema},
                                    "payees": {"type": "array", "items": payee_schema},
                                    "months": {"type": "array", "items": {"type": "object"}},
                                },
                                "required": ["id", "name", "accounts", "categories", "payees", "months"],
                            }
                        },
                        "required": ["plan"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_plan_settings",
            "description": "Get settings for a specific plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "settings": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Settings identifier"},
                                    "name": {"type": "string", "description": "Plan name"},
                                    "currency": {"type": "string", "description": "Currency code (e.g., USD, NOK)"},
                                    "first_month": {"type": "string", "description": "First month in YYYY-MM-DD format"},
                                    "last_month": {"type": "string", "description": "Last month in YYYY-MM-DD format"},
                                },
                                "required": ["id", "name"],
                            }
                        },
                        "required": ["settings"],
                    }
                },
                "required": ["data"],
            },
        },
        # Accounts tools
        {
            "name": "get_accounts",
            "description": "Get all accounts for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "accounts": {
                                "type": "array",
                                "items": account_schema,
                                "description": "List of all accounts for the plan"
                            }
                        },
                        "required": ["accounts"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_account",
            "description": "Get a specific account by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "account_id": {
                        "type": "string",
                        "description": "The account ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                },
                "required": ["plan_id", "account_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "account": account_schema,
                        },
                        "required": ["account"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "create_account",
            "description": "Create a new account",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "account": {
                        "allOf": [account_schema],
                        "description": "Account data with name, type, and balance (in milliunits). Required: name, type, balance.",
                    },
                },
                "required": ["plan_id", "account"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "account": account_schema,
                        },
                        "required": ["account"],
                    }
                },
                "required": ["data"],
            },
        },
        # Categories tools
        {
            "name": "get_categories",
            "description": "Get all categories for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "category_groups": {
                                "type": "array",
                                "items": category_group_schema,
                                "description": "List of category groups with their categories"
                            }
                        },
                        "required": ["category_groups"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_category",
            "description": "Get a specific category by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "category_id": {
                        "type": "string",
                        "description": "The category ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                },
                "required": ["plan_id", "category_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "category": category_schema,
                        },
                        "required": ["category"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "create_category",
            "description": "Create a new category",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "category": {
                        "allOf": [category_schema],
                        "description": "Category data including name and category_group_id. Required: name, category_group_id.",
                        "required": ["name", "category_group_id"],
                    },
                },
                "required": ["plan_id", "category"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "category": category_schema,
                        },
                        "required": ["category"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "update_category",
            "description": "Update an existing category",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "category_id": {
                        "type": "string",
                        "description": "The category ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                    "category": {
                        "allOf": [category_schema],
                        "description": "Category data to update. Required: name.",
                        "required": ["name"],
                    },
                },
                "required": ["plan_id", "category_id", "category"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "category": category_schema,
                        },
                        "required": ["category"],
                    }
                },
                "required": ["data"],
            },
        },
        # Payees tools
        {
            "name": "get_payees",
            "description": "Get all payees for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "payees": {
                                "type": "array",
                                "items": payee_schema,
                                "description": "List of all payees for the plan"
                            }
                        },
                        "required": ["payees"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_payee",
            "description": "Get a specific payee by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "payee_id": {
                        "type": "string",
                        "description": "The payee ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                },
                "required": ["plan_id", "payee_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "payee": payee_schema,
                        },
                        "required": ["payee"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "create_payee",
            "description": "Create a new payee",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "payee": {
                        "allOf": [payee_schema],
                        "description": "Payee data with name. Required: name.",
                        "required": ["name"],
                    },
                },
                "required": ["plan_id", "payee"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "payee": payee_schema,
                        },
                        "required": ["payee"],
                    }
                },
                "required": ["data"],
            },
        },
        # Months tools
        {
            "name": "get_months",
            "description": "Get all months for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "months": {
                                "type": "array",
                                "items": month_schema,
                                "description": "List of all months for the plan"
                            }
                        },
                        "required": ["months"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_month",
            "description": "Get a specific month for a plan",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "month": {
                        "type": "string",
                        "format": "date",
                        "description": "Month in YYYY-MM-DD format or 'current'",
                        "examples": ["2024-01-01", "current"]
                    },
                },
                "required": ["plan_id", "month"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "month": month_schema,
                        },
                        "required": ["month"],
                    }
                },
                "required": ["data"],
            },
        },
        # Transactions tools
        {
            "name": "get_transactions",
            "description": "Get transactions for a plan. All amounts are in milliunits (1/1000 of currency unit).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "since_date": common_params["since_date"],
                    "until_date": common_params["until_date"],
                    "type": {
                        "type": "string",
                        "enum": ["uncategorized", "unapproved"],
                        "description": "Filter by transaction type: 'uncategorized' for transactions without a category, 'unapproved' for transactions not yet approved",
                    },
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                    "limit": {"type": "integer", "description": "Maximum number of transactions to return (client-side pagination)", "minimum": 1},
                    "offset": {"type": "integer", "description": "Number of transactions to skip (client-side pagination)", "minimum": 0, "default": 0},
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "transactions": {
                                "type": "array",
                                "items": transaction_schema,
                                "description": "List of transactions matching the filter criteria"
                            }
                        },
                        "required": ["transactions"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_transaction",
            "description": "Get a specific transaction by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "transaction_id": {
                        "type": "string",
                        "description": "The transaction ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                },
                "required": ["plan_id", "transaction_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "transaction": transaction_schema,
                        },
                        "required": ["transaction"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "create_transaction",
            "description": "Create a new transaction. Amount must be in milliunits (1/1000 of currency unit).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "transaction": {
                        "allOf": [transaction_schema],
                        "description": "Single transaction data. Required: date, amount, account_id. Amount in milliunits.",
                        "required": ["date", "amount", "account_id"],
                    },
                },
                "required": ["plan_id", "transaction"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "transaction": transaction_schema,
                        },
                        "required": ["transaction"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "update_transaction",
            "description": "Update a single transaction. Amount must be in milliunits.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "transaction_id": {
                        "type": "string",
                        "description": "The transaction ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                    "transaction": {
                        "allOf": [transaction_schema],
                        "description": "Transaction data to update. Amount in milliunits.",
                    },
                },
                "required": ["plan_id", "transaction_id", "transaction"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "transaction": transaction_schema,
                        },
                        "required": ["transaction"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "update_transactions",
            "description": "Update multiple transactions at once. Each transaction must have an id or import_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "transactions": {
                        "type": "array",
                        "description": "List of transactions to update. Each must have id or import_id.",
                        "items": transaction_schema,
                        "minItems": 1,
                    },
                },
                "required": ["plan_id", "transactions"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "transactions": {
                                "type": "array",
                                "items": transaction_schema,
                                "description": "List of updated transactions"
                            }
                        },
                        "required": ["transactions"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "delete_transaction",
            "description": "Delete a transaction by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "transaction_id": {
                        "type": "string",
                        "description": "The transaction ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                },
                "required": ["plan_id", "transaction_id"],
            },
        },
        {
            "name": "import_transactions",
            "description": "Import transactions from linked accounts. Returns transactions in milliunits.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "transactions": {
                                "type": "array",
                                "items": transaction_schema,
                                "description": "List of imported transactions in milliunits"
                            }
                        },
                        "required": ["transactions"],
                    }
                },
                "required": ["data"],
            },
        },
        # Scheduled Transactions tools
        {
            "name": "get_scheduled_transactions",
            "description": "Get all scheduled transactions for a plan. Amounts are in milliunits.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "last_knowledge_of_server": common_params["last_knowledge_of_server"],
                },
                "required": ["plan_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "scheduled_transactions": {
                                "type": "array",
                                "items": scheduled_transaction_schema,
                                "description": "List of all scheduled transactions for the plan"
                            }
                        },
                        "required": ["scheduled_transactions"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "get_scheduled_transaction",
            "description": "Get a specific scheduled transaction by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "scheduled_transaction_id": {
                        "type": "string",
                        "description": "The scheduled transaction ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                },
                "required": ["plan_id", "scheduled_transaction_id"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "scheduled_transaction": scheduled_transaction_schema,
                        },
                        "required": ["scheduled_transaction"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "create_scheduled_transaction",
            "description": "Create a new scheduled transaction. Amount must be in milliunits.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "scheduled_transaction": {
                        "allOf": [scheduled_transaction_schema],
                        "description": "Scheduled transaction data. Required: date_first, frequency, amount (in milliunits).",
                        "required": ["date_first", "frequency", "amount"],
                    },
                },
                "required": ["plan_id", "scheduled_transaction"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "scheduled_transaction": scheduled_transaction_schema,
                        },
                        "required": ["scheduled_transaction"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "update_scheduled_transaction",
            "description": "Update a scheduled transaction. Amount must be in milliunits.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "scheduled_transaction_id": {
                        "type": "string",
                        "description": "The scheduled transaction ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
                    "scheduled_transaction": {
                        "allOf": [scheduled_transaction_schema],
                        "description": "Scheduled transaction data to update. Amount in milliunits.",
                    },
                },
                "required": ["plan_id", "scheduled_transaction_id", "scheduled_transaction"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "properties": {
                            "scheduled_transaction": scheduled_transaction_schema,
                        },
                        "required": ["scheduled_transaction"],
                    }
                },
                "required": ["data"],
            },
        },
        {
            "name": "delete_scheduled_transaction",
            "description": "Delete a scheduled transaction by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": common_params["plan_id"],
                    "scheduled_transaction_id": {
                        "type": "string",
                        "description": "The scheduled transaction ID (UUID)",
                        "examples": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
                    },
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
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        # Plans tools
        elif name == "get_plans":
            include_accounts = arguments.get("include_accounts", False)
            data = await client.get_plans(include_accounts=include_accounts)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_plan":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_plan(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_plan_settings":
            plan_id = arguments.get("plan_id")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_plan_settings(plan_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        # Accounts tools
        elif name == "get_accounts":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_accounts(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_account":
            plan_id = arguments.get("plan_id")
            account_id = arguments.get("account_id")
            if not plan_id or not account_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and account_id are required"}, "id": request_id}
            data = await client.get_account(plan_id, account_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "create_account":
            plan_id = arguments.get("plan_id")
            account_data = arguments.get("account")
            if not plan_id or not account_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and account are required"}, "id": request_id}
            data = await client.create_account(plan_id, account_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        # Categories tools
        elif name == "get_categories":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_categories(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_category":
            plan_id = arguments.get("plan_id")
            category_id = arguments.get("category_id")
            if not plan_id or not category_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and category_id are required"}, "id": request_id}
            data = await client.get_category(plan_id, category_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "create_category":
            plan_id = arguments.get("plan_id")
            category_data = arguments.get("category")
            if not plan_id or not category_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and category are required"}, "id": request_id}
            data = await client.create_category(plan_id, category_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "update_category":
            plan_id = arguments.get("plan_id")
            category_id = arguments.get("category_id")
            category_data = arguments.get("category")
            if not plan_id or not category_id or not category_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id, category_id, and category are required"}, "id": request_id}
            data = await client.update_category(plan_id, category_id, category_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        # Payees tools
        elif name == "get_payees":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_payees(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_payee":
            plan_id = arguments.get("plan_id")
            payee_id = arguments.get("payee_id")
            if not plan_id or not payee_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and payee_id are required"}, "id": request_id}
            data = await client.get_payee(plan_id, payee_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "create_payee":
            plan_id = arguments.get("plan_id")
            payee_data = arguments.get("payee")
            if not plan_id or not payee_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and payee are required"}, "id": request_id}
            data = await client.create_payee(plan_id, payee_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        # Months tools
        elif name == "get_months":
            plan_id = arguments.get("plan_id")
            last_knowledge = arguments.get("last_knowledge_of_server")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            data = await client.get_months(plan_id, last_knowledge_of_server=last_knowledge)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_month":
            plan_id = arguments.get("plan_id")
            month = arguments.get("month")
            if not plan_id or not month:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and month are required"}, "id": request_id}
            data = await client.get_month(plan_id, month)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
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
                
                content = [{ "type": "application/json", "text": json.dumps(data) }]
            except ValueError as e:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": str(e)}, "id": request_id}
        
        elif name == "get_transaction":
            plan_id = arguments.get("plan_id")
            transaction_id = arguments.get("transaction_id")
            if not plan_id or not transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and transaction_id are required"}, "id": request_id}
            data = await client.get_transaction(plan_id, transaction_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "create_transaction":
            plan_id = arguments.get("plan_id")
            if not plan_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id is required"}, "id": request_id}
            transaction_data = arguments.get("transaction") or arguments.get("transactions", {})
            data = await client.create_transaction(plan_id, transaction_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "update_transaction":
            plan_id = arguments.get("plan_id")
            transaction_id = arguments.get("transaction_id")
            transaction_data = arguments.get("transaction")
            if not plan_id or not transaction_id or not transaction_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id, transaction_id, and transaction are required"}, "id": request_id}
            data = await client.update_transaction(plan_id, transaction_id, transaction_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "update_transactions":
            plan_id = arguments.get("plan_id")
            transactions = arguments.get("transactions")
            if not plan_id or not transactions:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and transactions are required"}, "id": request_id}
            data = await client.update_transactions(plan_id, transactions)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "delete_transaction":
            plan_id = arguments.get("plan_id")
            transaction_id = arguments.get("transaction_id")
            if not plan_id or not transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and transaction_id are required"}, "id": request_id}
            data = await client.delete_transaction(plan_id, transaction_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
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
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "get_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            scheduled_transaction_id = arguments.get("scheduled_transaction_id")
            if not plan_id or not scheduled_transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and scheduled_transaction_id are required"}, "id": request_id}
            data = await client.get_scheduled_transaction(plan_id, scheduled_transaction_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "create_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            transaction_data = arguments.get("scheduled_transaction")
            if not plan_id or not transaction_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and scheduled_transaction are required"}, "id": request_id}
            data = await client.create_scheduled_transaction(plan_id, transaction_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "update_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            scheduled_transaction_id = arguments.get("scheduled_transaction_id")
            transaction_data = arguments.get("scheduled_transaction")
            if not plan_id or not scheduled_transaction_id or not transaction_data:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id, scheduled_transaction_id, and scheduled_transaction are required"}, "id": request_id}
            data = await client.update_scheduled_transaction(plan_id, scheduled_transaction_id, transaction_data)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
        elif name == "delete_scheduled_transaction":
            plan_id = arguments.get("plan_id")
            scheduled_transaction_id = arguments.get("scheduled_transaction_id")
            if not plan_id or not scheduled_transaction_id:
                return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "plan_id and scheduled_transaction_id are required"}, "id": request_id}
            data = await client.delete_scheduled_transaction(plan_id, scheduled_transaction_id)
            content = [{ "type": "application/json", "text": json.dumps(data) }]
        
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
                "text": json.dumps(result),
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
