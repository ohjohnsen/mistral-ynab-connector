"""YNAB API client for the MCP Connector."""

from typing import Any

import httpx

from config import settings


class YNABClient:
    """Client for interacting with the YNAB API."""

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
            method: HTTP method (GET, POST, PUT, DELETE).
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

    async def get_budgets(self) -> dict[str, Any]:
        """Get all budgets accessible with the API key."""
        return await self._make_request("GET", "/budgets")

    async def get_budget(self, budget_id: str) -> dict[str, Any]:
        """Get a specific budget by ID."""
        return await self._make_request("GET", f"/budgets/{budget_id}")

    async def get_categories(self, budget_id: str) -> dict[str, Any]:
        """Get all categories for a budget."""
        return await self._make_request("GET", f"/budgets/{budget_id}/categories")

    async def get_accounts(self, budget_id: str) -> dict[str, Any]:
        """Get all accounts for a budget."""
        return await self._make_request("GET", f"/budgets/{budget_id}/accounts")

    async def get_transactions(
        self,
        budget_id: str,
        account_id: str | None = None,
        since_date: str | None = None,
    ) -> dict[str, Any]:
        """Get transactions for a budget or account.

        Args:
            budget_id: The budget ID.
            account_id: Optional account ID to filter by.
            since_date: Optional date to get transactions since.
        """
        endpoint = f"/budgets/{budget_id}/transactions"
        params = {}
        if account_id:
            params["account_id"] = account_id
        if since_date:
            params["since_date"] = since_date
        return await self._make_request("GET", endpoint, params=params)

    async def create_transaction(
        self,
        budget_id: str,
        transaction_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new transaction.

        Args:
            budget_id: The budget ID.
            transaction_data: Transaction data as per YNAB API spec.
        """
        return await self._make_request(
            "POST",
            f"/budgets/{budget_id}/transactions",
            json_data={"transaction": transaction_data},
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
