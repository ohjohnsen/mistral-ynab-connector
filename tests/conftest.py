"""Pytest configuration and fixtures for YNAB MCP Connector tests."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config import Settings, settings
from mcp_server import app


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


# Register custom markers
def pytest_configure(config):
    """Register custom markers for pytest."""
    config.addinivalue_line(
        "markers", 
        "integration: mark test as integration test (makes real API calls)"
    )
