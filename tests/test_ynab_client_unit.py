"""Unit tests for YNABClient using mocking."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import httpx

from ynab_client import YNABClient
from config import Settings


# ============================================================================
# Fixture to mock settings
# ============================================================================

@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings to prevent loading real .env file."""
    test_settings = Settings(
        _env_file=None,
        ynab_api_key="",
        ynab_api_url="https://api.ynab.com/v1"
    )
    monkeypatch.setattr("ynab_client.settings", test_settings)
    return test_settings


# ============================================================================
# Initialization Tests
# ============================================================================

class TestYNABClientInitialization:
    """Unit tests for YNABClient initialization."""

    def test_default_initialization(self, mock_settings):
        """Test client initialization with default parameters."""
        client = YNABClient()
        
        assert client.api_key == ""
        assert client.base_url == "https://api.ynab.com/v1"

    def test_initialization_with_custom_key(self, mock_settings):
        """Test client initialization with custom API key."""
        client = YNABClient(api_key="custom_key_123")
        
        assert client.api_key == "custom_key_123"

    def test_initialization_with_custom_url(self, mock_settings):
        """Test client initialization with custom base URL."""
        client = YNABClient(base_url="https://custom.api.url/v1")
        
        assert client.base_url == "https://custom.api.url/v1"

    def test_initialization_with_both_custom(self, mock_settings):
        """Test client initialization with both custom key and URL."""
        client = YNABClient(
            api_key="custom_key",
            base_url="https://custom.api.url/v1"
        )
        
        assert client.api_key == "custom_key"
        assert client.base_url == "https://custom.api.url/v1"


# ============================================================================
# Headers Tests
# ============================================================================

class TestYNABClientHeaders:
    """Unit tests for YNABClient headers property."""

    def test_headers_with_api_key(self, mock_settings):
        """Test that headers are generated correctly."""
        client = YNABClient(api_key="test_key_123")
        headers = client.headers
        
        assert headers["Authorization"] == "Bearer test_key_123"
        assert headers["Content-Type"] == "application/json"

    def test_headers_without_api_key(self, mock_settings):
        """Test headers when API key is not set."""
        client = YNABClient(api_key="")
        headers = client.headers
        
        assert headers["Authorization"] == "Bearer "
        assert headers["Content-Type"] == "application/json"


# ============================================================================
# User Tests
# ============================================================================

class TestYNABClientUser:
    """Unit tests for user-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_user(self, mock_make_request, mock_settings):
        """Test get_user method."""
        mock_make_request.return_value = {
            "data": {
                "user": {
                    "id": "user-123",
                    "email": "test@example.com"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_user()
        
        assert result == {"data": {"user": {"id": "user-123", "email": "test@example.com"}}}
        mock_make_request.assert_awaited_once_with("GET", "/user")


# ============================================================================
# Plans Tests
# ============================================================================

class TestYNABClientPlans:
    """Unit tests for plan-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_plans_default(self, mock_make_request, mock_settings):
        """Test get_plans without include_accounts."""
        mock_make_request.return_value = {
            "data": {
                "plans": [
                    {"id": "plan-1", "name": "Test Plan"}
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_plans()
        
        assert result == {"data": {"plans": [{"id": "plan-1", "name": "Test Plan"}]}}
        mock_make_request.assert_awaited_once_with("GET", "/plans", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_plans_with_accounts(self, mock_make_request, mock_settings):
        """Test get_plans with include_accounts=True."""
        mock_make_request.return_value = {
            "data": {
                "plans": [
                    {
                        "id": "plan-1",
                        "name": "Test Plan",
                        "accounts": [{"id": "account-1", "name": "Checking"}]
                    }
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_plans(include_accounts=True)
        
        assert result["data"]["plans"][0]["accounts"] is not None
        mock_make_request.assert_awaited_once_with("GET", "/plans", params={"include_accounts": True})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_plan(self, mock_make_request, mock_settings):
        """Test get_plan method."""
        mock_make_request.return_value = {
            "data": {
                "plan": {
                    "id": "plan-123",
                    "name": "Test Plan",
                    "accounts": [],
                    "categories": [],
                    "payees": [],
                    "months": []
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_plan("plan-123")
        
        assert result["data"]["plan"]["id"] == "plan-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_plan_settings(self, mock_make_request, mock_settings):
        """Test get_plan_settings method."""
        mock_make_request.return_value = {
            "data": {
                "settings": {
                    "id": "settings-123",
                    "name": "Test Settings"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_plan_settings("plan-123")
        
        assert result["data"]["settings"]["id"] == "settings-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/settings")


# ============================================================================
# Accounts Tests
# ============================================================================

class TestYNABClientAccounts:
    """Unit tests for account-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_accounts(self, mock_make_request, mock_settings):
        """Test get_accounts method."""
        mock_make_request.return_value = {
            "data": {
                "accounts": [
                    {"id": "account-1", "name": "Checking", "type": "CHECKING"}
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_accounts("plan-123")
        
        assert len(result["data"]["accounts"]) == 1
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/accounts", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_account(self, mock_make_request, mock_settings):
        """Test get_account method."""
        mock_make_request.return_value = {
            "data": {
                "account": {
                    "id": "account-123",
                    "name": "Checking Account",
                    "type": "CHECKING",
                    "balance": 100000
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_account("plan-123", "account-123")
        
        assert result["data"]["account"]["id"] == "account-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/accounts/account-123")

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_create_account(self, mock_make_request, mock_settings):
        """Test create_account method."""
        mock_make_request.return_value = {
            "data": {
                "account": {
                    "id": "new-account-123",
                    "name": "New Account"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        account_data = {"name": "New Account", "type": "CHECKING", "balance": 0}
        result = await client.create_account("plan-123", account_data)
        
        assert result["data"]["account"]["id"] == "new-account-123"
        mock_make_request.assert_awaited_once_with("POST", "/plans/plan-123/accounts", json_data={"account": account_data})


# ============================================================================
# Categories Tests
# ============================================================================

class TestYNABClientCategories:
    """Unit tests for category-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_categories(self, mock_make_request, mock_settings):
        """Test get_categories method."""
        mock_make_request.return_value = {
            "data": {
                "category_groups": [
                    {
                        "id": "group-1",
                        "name": "Everyday Expenses",
                        "categories": [
                            {"id": "cat-1", "name": "Groceries"}
                        ]
                    }
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_categories("plan-123")
        
        assert len(result["data"]["category_groups"]) == 1
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/categories", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_category(self, mock_make_request, mock_settings):
        """Test get_category method."""
        mock_make_request.return_value = {
            "data": {
                "category": {
                    "id": "cat-123",
                    "name": "Groceries",
                    "category_group_id": "group-1"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_category("plan-123", "cat-123")
        
        assert result["data"]["category"]["id"] == "cat-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/categories/cat-123")

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_create_category(self, mock_make_request, mock_settings):
        """Test create_category method."""
        mock_make_request.return_value = {
            "data": {
                "category": {
                    "id": "new-cat-123",
                    "name": "New Category"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        category_data = {"name": "New Category", "category_group_id": "group-1"}
        result = await client.create_category("plan-123", category_data)
        
        assert result["data"]["category"]["id"] == "new-cat-123"
        mock_make_request.assert_awaited_once_with("POST", "/plans/plan-123/categories", json_data={"category": category_data})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_update_category(self, mock_make_request, mock_settings):
        """Test update_category method."""
        mock_make_request.return_value = {
            "data": {
                "category": {
                    "id": "cat-123",
                    "name": "Updated Category"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        category_data = {"name": "Updated Category"}
        result = await client.update_category("plan-123", "cat-123", category_data)
        
        assert result["data"]["category"]["name"] == "Updated Category"
        mock_make_request.assert_awaited_once_with("PATCH", "/plans/plan-123/categories/cat-123", json_data={"category": category_data})


# ============================================================================
# Transactions Tests
# ============================================================================

class TestYNABClientTransactions:
    """Unit tests for transaction-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_transactions(self, mock_make_request, mock_settings):
        """Test get_transactions method."""
        mock_make_request.return_value = {
            "data": {
                "transactions": [
                    {"id": "txn-1", "date": "2024-01-01", "amount": 100000}
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_transactions("plan-123")
        
        assert len(result["data"]["transactions"]) == 1
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/transactions", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_transaction(self, mock_make_request, mock_settings):
        """Test get_transaction method."""
        mock_make_request.return_value = {
            "data": {
                "transaction": {
                    "id": "txn-123",
                    "date": "2024-01-01",
                    "amount": 100000
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_transaction("plan-123", "txn-123")
        
        assert result["data"]["transaction"]["id"] == "txn-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/transactions/txn-123")

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_create_transaction(self, mock_make_request, mock_settings):
        """Test create_transaction method."""
        mock_make_request.return_value = {
            "data": {
                "transaction": {
                    "id": "new-txn-123"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        txn_data = {
            "transaction": {
                "date": "2024-01-01",
                "amount": 100000,
                "payee_name": "Test Payee",
                "account_id": "account-1"
            }
        }
        result = await client.create_transaction("plan-123", txn_data)
        
        assert result["data"]["transaction"]["id"] == "new-txn-123"
        mock_make_request.assert_awaited_once_with("POST", "/plans/plan-123/transactions", json_data={"transaction": txn_data["transaction"]})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_update_transaction(self, mock_make_request, mock_settings):
        """Test update_transaction method."""
        mock_make_request.return_value = {
            "data": {
                "transaction": {
                    "id": "txn-123",
                    "amount": 150000
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        txn_data = {"amount": 150000}
        result = await client.update_transaction("plan-123", "txn-123", txn_data)
        
        assert result["data"]["transaction"]["amount"] == 150000
        mock_make_request.assert_awaited_once_with("PUT", "/plans/plan-123/transactions/txn-123", json_data={"transaction": txn_data})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_delete_transaction(self, mock_make_request, mock_settings):
        """Test delete_transaction method."""
        mock_make_request.return_value = {}
        
        client = YNABClient(api_key="test_key")
        result = await client.delete_transaction("plan-123", "txn-123")
        
        assert result == {}
        mock_make_request.assert_awaited_once_with("DELETE", "/plans/plan-123/transactions/txn-123")


# ============================================================================
# Payees Tests
# ============================================================================

class TestYNABClientPayees:
    """Unit tests for payee-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_payees(self, mock_make_request, mock_settings):
        """Test get_payees method."""
        mock_make_request.return_value = {
            "data": {
                "payees": [
                    {"id": "payee-1", "name": "Grocery Store"}
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_payees("plan-123")
        
        assert len(result["data"]["payees"]) == 1
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/payees", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_payee(self, mock_make_request, mock_settings):
        """Test get_payee method."""
        mock_make_request.return_value = {
            "data": {
                "payee": {
                    "id": "payee-123",
                    "name": "Test Payee"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_payee("plan-123", "payee-123")
        
        assert result["data"]["payee"]["id"] == "payee-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/payees/payee-123")

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_create_payee(self, mock_make_request, mock_settings):
        """Test create_payee method."""
        mock_make_request.return_value = {
            "data": {
                "payee": {
                    "id": "new-payee-123",
                    "name": "New Payee"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        payee_data = {"name": "New Payee"}
        result = await client.create_payee("plan-123", payee_data)
        
        assert result["data"]["payee"]["id"] == "new-payee-123"
        mock_make_request.assert_awaited_once_with("POST", "/plans/plan-123/payees", json_data={"payee": payee_data})


# ============================================================================
# Months Tests
# ============================================================================

class TestYNABClientMonths:
    """Unit tests for month-related methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_months(self, mock_make_request, mock_settings):
        """Test get_months method."""
        mock_make_request.return_value = {
            "data": {
                "months": [
                    {"month": "2024-01", "note": "January"},
                    {"month": "2024-02", "note": "February"}
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_months("plan-123")
        
        assert len(result["data"]["months"]) == 2
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/months", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_month(self, mock_make_request, mock_settings):
        """Test get_month method."""
        mock_make_request.return_value = {
            "data": {
                "month": {
                    "month": "2024-01",
                    "categories": []
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_month("plan-123", "2024-01")
        
        assert result["data"]["month"]["month"] == "2024-01"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/months/2024-01")


# ============================================================================
# Scheduled Transactions Tests
# ============================================================================

class TestYNABClientScheduledTransactions:
    """Unit tests for scheduled transaction methods."""

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_scheduled_transactions(self, mock_make_request, mock_settings):
        """Test get_scheduled_transactions method."""
        mock_make_request.return_value = {
            "data": {
                "scheduled_transactions": [
                    {"id": "stxn-1", "date_first": "2024-01-01"}
                ]
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_scheduled_transactions("plan-123")
        
        assert len(result["data"]["scheduled_transactions"]) == 1
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/scheduled_transactions", params={})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_get_scheduled_transaction(self, mock_make_request, mock_settings):
        """Test get_scheduled_transaction method."""
        mock_make_request.return_value = {
            "data": {
                "scheduled_transaction": {
                    "id": "stxn-123"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        result = await client.get_scheduled_transaction("plan-123", "stxn-123")
        
        assert result["data"]["scheduled_transaction"]["id"] == "stxn-123"
        mock_make_request.assert_awaited_once_with("GET", "/plans/plan-123/scheduled_transactions/stxn-123")

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_create_scheduled_transaction(self, mock_make_request, mock_settings):
        """Test create_scheduled_transaction method."""
        mock_make_request.return_value = {
            "data": {
                "scheduled_transaction": {
                    "id": "new-stxn-123"
                }
            }
        }
        
        client = YNABClient(api_key="test_key")
        stxn_data = {"date_first": "2024-01-01", "amount": 100000}
        result = await client.create_scheduled_transaction("plan-123", stxn_data)
        
        assert result["data"]["scheduled_transaction"]["id"] == "new-stxn-123"
        mock_make_request.assert_awaited_once_with("POST", "/plans/plan-123/scheduled_transactions", json_data={"scheduled_transaction": stxn_data})

    @pytest.mark.asyncio
    @patch.object(YNABClient, "_make_request")
    async def test_delete_scheduled_transaction(self, mock_make_request, mock_settings):
        """Test delete_scheduled_transaction method."""
        mock_make_request.return_value = {}
        
        client = YNABClient(api_key="test_key")
        result = await client.delete_scheduled_transaction("plan-123", "stxn-123")
        
        assert result == {}
        mock_make_request.assert_awaited_once_with("DELETE", "/plans/plan-123/scheduled_transactions/stxn-123")
