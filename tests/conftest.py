"""Pytest configuration and fixtures for YNAB MCP Connector tests."""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, settings
from mcp_server import app
from ynab_client import YNABClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings with test values."""
    test_settings = Settings(
        ynab_api_key="test_api_key_12345",
        ynab_api_url="https://api.youneedabudget.com/v1",
        server_host="0.0.0.0",
        server_port=8000,
        mcp_name="YNAB Connector Test",
        mcp_version="0.1.0",
    )
    
    # Override the global settings
    monkeypatch.setattr("config.settings", test_settings)
    return test_settings


@pytest.fixture
def real_env_settings():
    """Load real settings from .env file for integration tests."""
    # This uses the actual .env file configured in the project
    return settings


@pytest.fixture
def mock_ynab_client(monkeypatch):
    """Create a mocked YNABClient with canned responses for unit tests.
    
    This fixture patches YNABClient to return mock data instead of making
    real API calls, allowing for fast unit testing without API dependencies.
    """
    mock_client = MagicMock(spec=YNABClient)
    
    # Mock user data
    mock_client.get_user.return_value = {
        "data": {
            "user": {
                "id": "test-user-id-12345",
                "email": "test@example.com"
            }
        }
    }
    
    # Mock plans data
    mock_client.get_plans.return_value = {
        "data": {
            "plans": [
                {
                    "id": "test-plan-id-001",
                    "name": "Test Plan 1",
                    "settings": {"id": "test-settings-id-001"}
                },
                {
                    "id": "test-plan-id-002",
                    "name": "Test Plan 2",
                    "settings": {"id": "test-settings-id-002"}
                }
            ]
        }
    }
    
    # Mock get_plan data
    def mock_get_plan(plan_id=None, **kwargs):
        return {
            "data": {
                "plan": {
                    "id": plan_id or "test-plan-id-001",
                    "name": "Test Plan",
                    "accounts": [
                        {"id": "test-account-id-001", "name": "Checking"},
                        {"id": "test-account-id-002", "name": "Savings"}
                    ],
                    "categories": [],
                    "payees": [],
                    "months": []
                }
            }
        }
    mock_client.get_plan.side_effect = mock_get_plan
    
    # Mock plan settings
    mock_client.get_plan_settings.return_value = {
        "data": {
            "settings": {
                "id": "test-settings-id",
                "name": "Test Plan Settings"
            }
        }
    }
    
    # Mock accounts
    mock_client.get_accounts.return_value = {
        "data": {
            "accounts": [
                {"id": "test-account-id-001", "name": "Checking", "type": "CHECKING"},
                {"id": "test-account-id-002", "name": "Savings", "type": "SAVINGS"}
            ]
        }
    }
    
    # Mock get_account for individual account
    mock_client.get_account.return_value = {
        "data": {
            "account": {
                "id": "test-account-id-001",
                "name": "Checking Account",
                "type": "CHECKING",
                "balance": 100000,
                "cleared_balance": 90000,
                "uncleared_balance": 10000
            }
        }
    }
    
    # Mock transactions
    mock_client.get_transactions.return_value = {
        "data": {
            "transactions": [
                {
                    "id": "test-transaction-id-001",
                    "date": "2024-01-15",
                    "amount": 100000,
                    "payee_name": "Grocery Store",
                    "category_name": "Food",
                    "account_id": "test-account-id-001",
                    "cleared": "cleared",
                    "approved": True
                },
                {
                    "id": "test-transaction-id-002",
                    "date": "2024-01-16",
                    "amount": 50000,
                    "payee_name": "Gas Station",
                    "category_name": "Transportation",
                    "account_id": "test-account-id-001",
                    "cleared": "cleared",
                    "approved": True
                },
                {
                    "id": "test-transaction-id-003",
                    "date": "2024-01-17",
                    "amount": 75000,
                    "payee_name": "Restaurant",
                    "category_name": "Food",
                    "account_id": "test-account-id-002",
                    "cleared": "uncategorized",
                    "approved": False
                }
            ]
        }
    }
    
    # Mock get_transaction for individual transaction
    mock_client.get_transaction.return_value = {
        "data": {
            "transaction": {
                "id": "test-transaction-id-001",
                "date": "2024-01-15",
                "amount": 100000,
                "payee_name": "Grocery Store",
                "category_name": "Food",
                "account_id": "test-account-id-001",
                "cleared": "cleared",
                "approved": True
            }
        }
    }
    
    # Make async methods return AsyncMock for compatibility
    mock_client._make_request = AsyncMock()
    
    # Patch the YNABClient class in both ynab_client and mcp_server modules
    monkeypatch.setattr("ynab_client.YNABClient", lambda *args, **kwargs: mock_client)
    monkeypatch.setattr("mcp_server.YNABClient", lambda *args, **kwargs: mock_client)
    
    return mock_client


# Register custom markers
def pytest_configure(config):
    """Register custom markers for pytest."""
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test (makes real API calls)"
    )
