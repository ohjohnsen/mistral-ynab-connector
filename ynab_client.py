"""YNAB API client aligned with official OpenAPI specification.

This client implements the YNAB API v1.85.0 as documented in their OpenAPI spec.
All endpoints use /plans/ terminology and follow the official API structure.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import settings


class YNABClient:
    """Client for interacting with the YNAB API v1.
    
    Aligned with official OpenAPI specification at:
    https://api.ynab.com
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        """Initialize the YNAB client.

        Args:
            api_key: YNAB API key. If not provided, uses settings.ynab_api_key.
            base_url: YNAB API base URL. If not provided, uses settings.ynab_api_url.
        """
        self.api_key = api_key or settings.ynab_api_key
        self.base_url = base_url or settings.ynab_api_url
        self._client = httpx.Client()

    @property
    def headers(self) -> dict[str, str]:
        """Generate headers for API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the YNAB API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH).
            endpoint: API endpoint path (without base URL).
            params: Query parameters.
            json_data: Request body as JSON.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # User Endpoints
    # =========================================================================

    async def get_user(self) -> dict[str, Any]:
        """Get authenticated user information.
        
        GET /user
        """
        return await self._make_request("GET", "/user")

    # =========================================================================
    # Plans Endpoints
    # =========================================================================

    async def get_plans(self, include_accounts: bool = False) -> dict[str, Any]:
        """Get all plans.
        
        GET /plans
        
        Args:
            include_accounts: Whether to include the list of plan accounts.
        """
        params = {}
        if include_accounts:
            params["include_accounts"] = True
        return await self._make_request("GET", "/plans", params=params)

    async def get_plan(self, plan_id: str, last_knowledge_of_server: int | None = None) -> dict[str, Any]:
        """Get a single plan with all related entities.
        
        GET /plans/{plan_id}
        
        Args:
            plan_id: The id of the plan. Can be "last-used" or "default".
            last_knowledge_of_server: Starting server knowledge for delta request.
        """
        params = {}
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}", params=params)

    async def get_plan_settings(self, plan_id: str) -> dict[str, Any]:
        """Get settings for a plan.
        
        GET /plans/{plan_id}/settings
        
        Args:
            plan_id: The id of the plan. Can be "last-used" or "default".
        """
        return await self._make_request("GET", f"/plans/{plan_id}/settings")

    # =========================================================================
    # Accounts Endpoints
    # =========================================================================

    async def get_accounts(self, plan_id: str, last_knowledge_of_server: int | None = None) -> dict[str, Any]:
        """Get all accounts for a plan.
        
        GET /plans/{plan_id}/accounts
        
        Args:
            plan_id: The id of the plan. Can be "last-used" or "default".
            last_knowledge_of_server: Starting server knowledge for delta request.
        """
        params = {}
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}/accounts", params=params)

    async def get_account(self, plan_id: str, account_id: str) -> dict[str, Any]:
        """Get a single account.
        
        GET /plans/{plan_id}/accounts/{account_id}
        
        Args:
            plan_id: The id of the plan.
            account_id: The id of the account (UUID).
        """
        return await self._make_request("GET", f"/plans/{plan_id}/accounts/{account_id}")

    async def create_account(self, plan_id: str, account_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new account.
        
        POST /plans/{plan_id}/accounts
        
        Args:
            plan_id: The id of the plan.
            account_data: Account data with name, type, and balance (in milliunits).
        """
        return await self._make_request(
            "POST",
            f"/plans/{plan_id}/accounts",
            json_data={"account": account_data},
        )

    # =========================================================================
    # Categories Endpoints
    # =========================================================================

    async def get_categories(self, plan_id: str, last_knowledge_of_server: int | None = None) -> dict[str, Any]:
        """Get all categories grouped by category group.
        
        GET /plans/{plan_id}/categories
        
        Args:
            plan_id: The id of the plan. Can be "last-used" or "default".
            last_knowledge_of_server: Starting server knowledge for delta request.
        """
        params = {}
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}/categories", params=params)

    async def get_category(self, plan_id: str, category_id: str) -> dict[str, Any]:
        """Get a single category.
        
        GET /plans/{plan_id}/categories/{category_id}
        
        Args:
            plan_id: The id of the plan.
            category_id: The id of the category.
        """
        return await self._make_request("GET", f"/plans/{plan_id}/categories/{category_id}")

    async def create_category(self, plan_id: str, category_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new category.
        
        POST /plans/{plan_id}/categories
        
        Args:
            plan_id: The id of the plan.
            category_data: Category data including name and category_group_id.
        """
        return await self._make_request(
            "POST",
            f"/plans/{plan_id}/categories",
            json_data={"category": category_data},
        )

    async def update_category(self, plan_id: str, category_id: str, category_data: dict[str, Any]) -> dict[str, Any]:
        """Update a category.
        
        PATCH /plans/{plan_id}/categories/{category_id}
        """
        return await self._make_request(
            "PATCH",
            f"/plans/{plan_id}/categories/{category_id}",
            json_data={"category": category_data},
        )

    async def get_month_category(self, plan_id: str, month: str, category_id: str) -> dict[str, Any]:
        """Get a category for a specific plan month.
        
        GET /plans/{plan_id}/months/{month}/categories/{category_id}
        """
        return await self._make_request("GET", f"/plans/{plan_id}/months/{month}/categories/{category_id}")

    async def update_month_category(self, plan_id: str, month: str, category_id: str, budgeted: int) -> dict[str, Any]:
        """Update category budgeted amount for a specific month.
        
        PATCH /plans/{plan_id}/months/{month}/categories/{category_id}
        """
        return await self._make_request(
            "PATCH",
            f"/plans/{plan_id}/months/{month}/categories/{category_id}",
            json_data={"category": {"budgeted": budgeted}},
        )

    # =========================================================================
    # Category Groups Endpoints
    # =========================================================================

    async def create_category_group(self, plan_id: str, group_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new category group.
        
        POST /plans/{plan_id}/category_groups
        """
        return await self._make_request(
            "POST",
            f"/plans/{plan_id}/category_groups",
            json_data={"category_group": group_data},
        )

    async def update_category_group(self, plan_id: str, category_group_id: str, group_data: dict[str, Any]) -> dict[str, Any]:
        """Update a category group.
        
        PATCH /plans/{plan_id}/category_groups/{category_group_id}
        """
        return await self._make_request(
            "PATCH",
            f"/plans/{plan_id}/category_groups/{category_group_id}",
            json_data={"category_group": group_data},
        )

    # =========================================================================
    # Payees Endpoints
    # =========================================================================

    async def get_payees(self, plan_id: str, last_knowledge_of_server: int | None = None) -> dict[str, Any]:
        """Get all payees for a plan.
        
        GET /plans/{plan_id}/payees
        """
        params = {}
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}/payees", params=params)

    async def get_payee(self, plan_id: str, payee_id: str) -> dict[str, Any]:
        """Get a single payee.
        
        GET /plans/{plan_id}/payees/{payee_id}
        """
        return await self._make_request("GET", f"/plans/{plan_id}/payees/{payee_id}")

    async def create_payee(self, plan_id: str, payee_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new payee.
        
        POST /plans/{plan_id}/payees
        """
        return await self._make_request(
            "POST",
            f"/plans/{plan_id}/payees",
            json_data={"payee": payee_data},
        )

    async def update_payee(self, plan_id: str, payee_id: str, payee_data: dict[str, Any]) -> dict[str, Any]:
        """Update a payee.
        
        PATCH /plans/{plan_id}/payees/{payee_id}
        """
        return await self._make_request(
            "PATCH",
            f"/plans/{plan_id}/payees/{payee_id}",
            json_data={"payee": payee_data},
        )

    # =========================================================================
    # Payee Locations Endpoints
    # =========================================================================

    async def get_payee_locations(self, plan_id: str) -> dict[str, Any]:
        """Get all payee locations for a plan.
        
        GET /plans/{plan_id}/payee_locations
        """
        return await self._make_request("GET", f"/plans/{plan_id}/payee_locations")

    async def get_payee_location(self, plan_id: str, payee_location_id: str) -> dict[str, Any]:
        """Get a single payee location.
        
        GET /plans/{plan_id}/payee_locations/{payee_location_id}
        """
        return await self._make_request("GET", f"/plans/{plan_id}/payee_locations/{payee_location_id}")

    async def get_payee_locations_by_payee(self, plan_id: str, payee_id: str) -> dict[str, Any]:
        """Get all locations for a specific payee.
        
        GET /plans/{plan_id}/payees/{payee_id}/payee_locations
        """
        return await self._make_request("GET", f"/plans/{plan_id}/payees/{payee_id}/payee_locations")

    # =========================================================================
    # Months Endpoints
    # =========================================================================

    async def get_months(self, plan_id: str, last_knowledge_of_server: int | None = None) -> dict[str, Any]:
        """Get all plan months.
        
        GET /plans/{plan_id}/months
        """
        params = {}
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}/months", params=params)

    async def get_month(self, plan_id: str, month: str) -> dict[str, Any]:
        """Get a single plan month.
        
        GET /plans/{plan_id}/months/{month}
        
        Args:
            month: ISO format date (e.g. 2024-01-01) or "current".
        """
        return await self._make_request("GET", f"/plans/{plan_id}/months/{month}")

    # =========================================================================
    # Transactions Endpoints
    # =========================================================================

    async def get_transactions(
        self,
        plan_id: str,
        since_date: str | None = None,
        until_date: str | None = None,
        type_filter: str | None = None,
        last_knowledge_of_server: int | None = None,
    ) -> dict[str, Any]:
        """Get transactions for a plan.
        
        GET /plans/{plan_id}/transactions
        
        Args:
            type_filter: "uncategorized" or "unapproved".
        """
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if until_date:
            params["until_date"] = until_date
        if type_filter:
            params["type"] = type_filter
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}/transactions", params=params)

    async def get_transaction(self, plan_id: str, transaction_id: str) -> dict[str, Any]:
        """Get a single transaction.
        
        GET /plans/{plan_id}/transactions/{transaction_id}
        """
        return await self._make_request("GET", f"/plans/{plan_id}/transactions/{transaction_id}")

    async def create_transaction(self, plan_id: str, transaction_data: dict[str, Any]) -> dict[str, Any]:
        """Create transaction(s).
        
        POST /plans/{plan_id}/transactions
        
        Args:
            transaction_data: {"transaction": {...}} or {"transactions": [...]}
        """
        return await self._make_request("POST", f"/plans/{plan_id}/transactions", json_data=transaction_data)

    async def update_transaction(self, plan_id: str, transaction_id: str, transaction_data: dict[str, Any]) -> dict[str, Any]:
        """Update a transaction.
        
        PUT /plans/{plan_id}/transactions/{transaction_id}
        """
        return await self._make_request(
            "PUT",
            f"/plans/{plan_id}/transactions/{transaction_id}",
            json_data={"transaction": transaction_data},
        )

    async def update_transactions(self, plan_id: str, transactions: list[dict[str, Any]]) -> dict[str, Any]:
        """Update multiple transactions.
        
        PATCH /plans/{plan_id}/transactions
        """
        return await self._make_request(
            "PATCH",
            f"/plans/{plan_id}/transactions",
            json_data={"transactions": transactions},
        )

    async def delete_transaction(self, plan_id: str, transaction_id: str) -> dict[str, Any]:
        """Delete a transaction.
        
        DELETE /plans/{plan_id}/transactions/{transaction_id}
        """
        return await self._make_request("DELETE", f"/plans/{plan_id}/transactions/{transaction_id}")

    async def import_transactions(self, plan_id: str) -> dict[str, Any]:
        """Import transactions from linked accounts.
        
        POST /plans/{plan_id}/transactions/import
        """
        return await self._make_request("POST", f"/plans/{plan_id}/transactions/import")

    async def get_account_transactions(
        self,
        plan_id: str,
        account_id: str,
        since_date: str | None = None,
        until_date: str | None = None,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get transactions for a specific account.
        
        GET /plans/{plan_id}/accounts/{account_id}/transactions
        """
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if until_date:
            params["until_date"] = until_date
        if type_filter:
            params["type"] = type_filter
        return await self._make_request("GET", f"/plans/{plan_id}/accounts/{account_id}/transactions", params=params)

    async def get_category_transactions(
        self,
        plan_id: str,
        category_id: str,
        since_date: str | None = None,
        until_date: str | None = None,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get transactions for a specific category.
        
        GET /plans/{plan_id}/categories/{category_id}/transactions
        """
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if until_date:
            params["until_date"] = until_date
        if type_filter:
            params["type"] = type_filter
        return await self._make_request("GET", f"/plans/{plan_id}/categories/{category_id}/transactions", params=params)

    async def get_payee_transactions(
        self,
        plan_id: str,
        payee_id: str,
        since_date: str | None = None,
        until_date: str | None = None,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get transactions for a specific payee.
        
        GET /plans/{plan_id}/payees/{payee_id}/transactions
        """
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if until_date:
            params["until_date"] = until_date
        if type_filter:
            params["type"] = type_filter
        return await self._make_request("GET", f"/plans/{plan_id}/payees/{payee_id}/transactions", params=params)

    async def get_month_transactions(
        self,
        plan_id: str,
        month: str,
        since_date: str | None = None,
        until_date: str | None = None,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get transactions for a specific month.
        
        GET /plans/{plan_id}/months/{month}/transactions
        """
        params: dict[str, Any] = {}
        if since_date:
            params["since_date"] = since_date
        if until_date:
            params["until_date"] = until_date
        if type_filter:
            params["type"] = type_filter
        return await self._make_request("GET", f"/plans/{plan_id}/months/{month}/transactions", params=params)

    # =========================================================================
    # Scheduled Transactions Endpoints
    # =========================================================================

    async def get_scheduled_transactions(self, plan_id: str, last_knowledge_of_server: int | None = None) -> dict[str, Any]:
        """Get all scheduled transactions for a plan.
        
        GET /plans/{plan_id}/scheduled_transactions
        """
        params = {}
        if last_knowledge_of_server is not None:
            params["last_knowledge_of_server"] = last_knowledge_of_server
        return await self._make_request("GET", f"/plans/{plan_id}/scheduled_transactions", params=params)

    async def get_scheduled_transaction(self, plan_id: str, scheduled_transaction_id: str) -> dict[str, Any]:
        """Get a single scheduled transaction.
        
        GET /plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}
        """
        return await self._make_request("GET", f"/plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}")

    async def create_scheduled_transaction(self, plan_id: str, transaction_data: dict[str, Any]) -> dict[str, Any]:
        """Create a scheduled transaction.
        
        POST /plans/{plan_id}/scheduled_transactions
        """
        return await self._make_request(
            "POST",
            f"/plans/{plan_id}/scheduled_transactions",
            json_data={"scheduled_transaction": transaction_data},
        )

    async def update_scheduled_transaction(self, plan_id: str, scheduled_transaction_id: str, transaction_data: dict[str, Any]) -> dict[str, Any]:
        """Update a scheduled transaction.
        
        PUT /plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}
        """
        return await self._make_request(
            "PUT",
            f"/plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}",
            json_data={"scheduled_transaction": transaction_data},
        )

    async def delete_scheduled_transaction(self, plan_id: str, scheduled_transaction_id: str) -> dict[str, Any]:
        """Delete a scheduled transaction.
        
        DELETE /plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}
        """
        return await self._make_request("DELETE", f"/plans/{plan_id}/scheduled_transactions/{scheduled_transaction_id}")

    # =========================================================================
    # Money Movements Endpoints
    # =========================================================================

    async def get_money_movements(self, plan_id: str) -> dict[str, Any]:
        """Get all money movements for a plan.
        
        GET /plans/{plan_id}/money_movements
        """
        return await self._make_request("GET", f"/plans/{plan_id}/money_movements")

    async def get_month_money_movements(self, plan_id: str, month: str) -> dict[str, Any]:
        """Get money movements for a specific month.
        
        GET /plans/{plan_id}/months/{month}/money_movements
        """
        return await self._make_request("GET", f"/plans/{plan_id}/months/{month}/money_movements")

    async def get_money_movement_groups(self, plan_id: str) -> dict[str, Any]:
        """Get all money movement groups for a plan.
        
        GET /plans/{plan_id}/money_movement_groups
        """
        return await self._make_request("GET", f"/plans/{plan_id}/money_movement_groups")

    async def get_month_money_movement_groups(self, plan_id: str, month: str) -> dict[str, Any]:
        """Get money movement groups for a specific month.
        
        GET /plans/{plan_id}/months/{month}/money_movement_groups
        """
        return await self._make_request("GET", f"/plans/{plan_id}/months/{month}/money_movement_groups")

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
