"""Tests for FastAPI endpoints."""

import pytest

from config import settings


class TestHealthEndpoint:
    """Tests for the /mcp/health endpoint."""

    def test_health_check_returns_200(self, test_client):
        """Test that the health check endpoint returns 200 OK."""
        response = test_client.get("/mcp/health")
        
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "version": settings.mcp_version
        }


class TestInfoEndpoint:
    """Tests for the /mcp/info endpoint."""

    def test_info_returns_200(self, test_client):
        """Test that the info endpoint returns 200 OK."""
        response = test_client.get("/mcp/info")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "api_version" in data
        assert "base_url" in data
        assert "capabilities" in data

    def test_info_returns_expected_structure(self, test_client):
        """Test that the info endpoint returns the expected structure."""
        response = test_client.get("/mcp/info")
        data = response.json()
        
        # Check top-level fields
        assert data["name"] == "YNAB Connector"
        assert data["version"] == settings.mcp_version
        assert "YNAB API Connector aligned with official OpenAPI spec" in data["description"]
        assert data["api_version"] == "1.85.0"
        
        # Check capabilities structure
        assert "user" in data["capabilities"]
        assert "plans" in data["capabilities"]
        assert "accounts" in data["capabilities"]
        assert "transactions" in data["capabilities"]


class TestServerCardEndpoint:
    """Tests for the /.well-known/mcp/server-card endpoint."""

    def test_server_card_returns_200(self, test_client):
        """Test that the server card endpoint returns 200 OK."""
        response = test_client.get("/.well-known/mcp/server-card")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "name" in data
        assert "description" in data
        assert "version" in data
        assert "url" in data

    def test_server_card_returns_expected_structure(self, test_client):
        """Test that the server card returns expected MCP discovery format."""
        response = test_client.get("/.well-known/mcp/server-card")
        data = response.json()
        
        assert data["name"] == "YNAB Connector"
        assert data["version"] == settings.mcp_version
        assert data["url"] == "/mcp"
        assert "auth" in data
        assert data["auth"]["type"] == "api_key"
        assert data["auth"]["headerName"] == "Authorization"
        assert "capabilities" in data
