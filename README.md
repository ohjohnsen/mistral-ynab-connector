# YNAB MCP Connector

A Model Context Protocol (MCP) connector for You Need A Budget (YNAB) that exposes YNAB API functionality to AI assistants like Mistral.

## Features

- **MCP Standard Endpoints**: Health checks, server info, and capabilities
- **Budget Management**: List and retrieve YNAB budget details
- **Category Access**: Browse budget categories
- **Account Management**: View all accounts in a budget
- **Transaction Handling**: Read and create transactions
- **Resource Discovery**: MCP-compatible resource endpoints for budgets, accounts, and categories
- **Tool Integration**: MCP tool endpoints for AI assistant integration

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- A [YNAB Personal Access Token](https://api.youneedabudget.com/#personal-access-tokens)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd mistral-ynab-connector
```

### 2. Install Dependencies

```bash
uv sync
```

This installs all required dependencies:
- FastAPI
- Uvicorn
- Pydantic
- HTTPX

### 3. Configure Your YNAB API Key

Copy the example environment file and add your YNAB API key:

```bash
cp .env.example .env
```

Edit `.env` and set your YNAB API key:

```bash
YNAB_API_KEY=your_personal_access_token_here
```

You can also set it as an environment variable:

```bash
export YNAB_API_KEY=your_personal_access_token_here
```

### 4. Run the Server

```bash
uv run python main.py
```

The server will start on `http://0.0.0.0:8000` with auto-reload enabled.

### 5. Verify It Works

```bash
curl http://localhost:8000/mcp/health
# {"status":"healthy","version":"0.1.0"}
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `YNAB_API_KEY` | Yes | - | Your YNAB Personal Access Token |
| `YNAB_API_URL` | No | `https://api.youneedabudget.com/v1` | YNAB API base URL |
| `SERVER_HOST` | No | `0.0.0.0` | Server host address |
| `SERVER_PORT` | No | `8000` | Server port |
| `MCP_NAME` | No | `YNAB Connector` | MCP server name |
| `MCP_VERSION` | No | `0.1.0` | MCP server version |

## API Endpoints

### MCP Standard Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mcp/health` | Health check endpoint |
| GET | `/mcp/info` | Server information and capabilities |

### MCP Resource Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mcp/resources/budgets` | List all budgets as MCP resources |
| GET | `/mcp/resources/budgets/{budget_id}/accounts` | List accounts for a budget |
| GET | `/mcp/resources/budgets/{budget_id}/categories` | List categories for a budget |

### MCP Tool Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mcp/tools/get_budget` | Get budget details |
| POST | `/mcp/tools/get_transactions` | Get transactions for a budget |
| POST | `/mcp/tools/create_transaction` | Create a new transaction |

### Direct YNAB API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/budgets` | List all accessible budgets |
| GET | `/api/budgets/{budget_id}` | Get a specific budget |
| GET | `/api/budgets/{budget_id}/categories` | Get all categories for a budget |
| GET | `/api/budgets/{budget_id}/accounts` | Get all accounts for a budget |
| GET | `/api/budgets/{budget_id}/transactions` | List transactions (with optional filters) |
| POST | `/api/budgets/{budget_id}/transactions` | Create a new transaction |

### Query Parameters

For `/api/budgets/{budget_id}/transactions`:
- `account_id` (optional): Filter by account ID
- `since_date` (optional): Get transactions since date (format: YYYY-MM-DD)

### Swagger UI

Interactive API documentation is available at:

```
http://localhost:8000/docs
```

## MCP Integration

This connector implements the Model Context Protocol (MCP) specification, allowing AI assistants to interact with YNAB data.

### Resource URIs

- Budgets: `ynab://budget/{budget_id}`
- Accounts: `ynab://account/{account_id}`
- Categories: `ynab://category/{category_id}`

### Example MCP Tool Calls

**Get Budget:**
```json
{
  "budget_id": "your-budget-id"
}
```

**Get Transactions:**
```json
{
  "budget_id": "your-budget-id",
  "account_id": "your-account-id",
  "since_date": "2024-01-01"
}
```

**Create Transaction:**
```json
{
  "budget_id": "your-budget-id",
  "transaction": {
    "account_id": "your-account-id",
    "date": "2024-01-15",
    "amount": 100000,
    "payee_name": "Grocery Store",
    "category_id": "your-category-id",
    "memo": "Weekly groceries",
    "cleared": "cleared",
    "approved": true
  }
}
```

Note: Amounts are in milliunits (e.g., $100 = 100000).

## Project Structure

```
mistral-ynab-connector/
├── main.py              # Server entry point
├── config.py            # Configuration management
├── mcp_server.py        # FastAPI application with endpoints
├── ynab_client.py       # YNAB API client
├── pyproject.toml       # Project configuration
├── .env.example         # Environment template
├── .gitignore
└── README.md
```

## Development

### Install Dev Dependencies

```bash
uv sync --all-extras
```

### Run Tests

```bash
uv run pytest
```

### Run Linter

```bash
uv run ruff check .
```

## License

This project is provided as-is for use with Mistral and YNAB.

## YNAB API Documentation

For more information on the YNAB API, see:
https://api.youneedabudget.com/
