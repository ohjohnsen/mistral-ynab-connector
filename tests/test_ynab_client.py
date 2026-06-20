"""Tests for the YNAB client using real API token from .env."""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from config import settings
from ynab_client import YNABClient


# Mark all tests in this module as integration tests since they use real API calls
pytestmark = pytest.mark.integration


class TestYNABClientInitialization:
    """Tests for YNAB client initialization."""

    def test_client_initialization_with_env_key(self, real_env_settings):
        """Test that client initializes with API key from environment."""
        if not settings.ynab_api_key:
            pytest.skip("YNAB_API_KEY not configured in environment")

        # This test uses the real API key from .env
        client = YNABClient()
        
        assert client.api_key == settings.ynab_api_key
        assert client.base_url == settings.ynab_api_url
        assert client.api_key is not None
        assert len(client.api_key) > 0

    def test_client_initialization_with_custom_key(self):
        """Test that client can be initialized with a custom API key."""
        custom_key = "custom_test_key_12345"
        custom_url = "https://custom.api.url/v1"
        
        client = YNABClient(api_key=custom_key, base_url=custom_url)
        
        assert client.api_key == custom_key
        assert client.base_url == custom_url

    def test_client_headers_property(self, real_env_settings):
        """Test that client generates correct headers."""
        client = YNABClient()
        headers = client.headers
        
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Authorization"] == f"Bearer {settings.ynab_api_key}"
        assert headers["Content-Type"] == "application/json"


class TestYNABClientUser:
    """Tests for YNAB client user endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_with_real_token(self, real_env_settings):
        """Test the get_user method with real API token from .env.
        
        This is an integration test that makes a real API call to YNAB.
        It will be skipped if YNAB_API_KEY is not set.
        """
        if not settings.ynab_api_key or settings.ynab_api_key == "":
            pytest.skip("YNAB_API_KEY not configured in environment")
        
        client = YNABClient()
        
        try:
            # Make the actual API call
            user_data = await client.get_user()
            
            # Verify we got valid response
            assert user_data is not None
            assert isinstance(user_data, dict)
            assert "data" in user_data
            assert "user" in user_data["data"]
            
            user = user_data["data"]["user"]
            assert "id" in user
            # Email may or may not be present depending on API version
            
        except httpx.HTTPStatusError as e:
            # If the token is invalid, we'll get a 401 - that's okay for testing
            # the client is working correctly
            if e.response.status_code == 401:
                pytest.skip("Invalid YNAB API token in .env file")
            else:
                raise


class TestYNABClientPlans:
    """Tests for YNAB client plans endpoint."""

    @pytest.mark.asyncio
    async def test_get_plans_with_real_token(self, real_env_settings):
        """Test the get_plans method with real API token from .env.
        
        This is an integration test that makes a real API call to YNAB.
        """
        if not settings.ynab_api_key or settings.ynab_api_key == "":
            pytest.skip("YNAB_API_KEY not configured in environment")
        
        client = YNABClient()
        
        try:
            # Make the actual API call
            plans_data = await client.get_plans()
            
            # Verify we got valid response
            assert plans_data is not None
            assert isinstance(plans_data, dict)
            assert "data" in plans_data
            assert "plans" in plans_data["data"]
            
        except httpx.HTTPStatusError as e:
            # If the token is invalid, we'll get a 401 - that's okay for testing
            if e.response.status_code == 401:
                pytest.skip("Invalid YNAB API token in .env file")
            else:
                raise

    @pytest.mark.asyncio
    async def test_get_plans_with_include_accounts(self, real_env_settings):
        """Test get_plans with include_accounts parameter."""
        if not settings.ynab_api_key or settings.ynab_api_key == "":
            pytest.skip("YNAB_API_KEY not configured in environment")
        
        client = YNABClient()
        
        try:
            # Make the actual API call with include_accounts=True
            plans_data = await client.get_plans(include_accounts=True)
            
            # Verify we got valid response
            assert plans_data is not None
            assert isinstance(plans_data, dict)
            assert "data" in plans_data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                pytest.skip("Invalid YNAB API token in .env file")
            else:
                raise
