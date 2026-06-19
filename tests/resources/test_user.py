"""Tests for user resource operations via MCP endpoint."""

import pytest


class TestUserResourceList:
    """Tests for listing user resources."""

    def test_resources_list_includes_user(self, test_client, mock_settings):
        """Test that resources/list includes the user resource."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        resources = data["result"]["resources"]
        
        uris = [r["uri"] for r in resources]
        assert "ynab://user" in uris

    def test_user_resource_has_correct_fields(self, test_client, mock_settings):
        """Test that the user resource has correct metadata."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        user_resource = next(
            (r for r in resources if r["uri"] == "ynab://user"),
            None
        )
        
        assert user_resource is not None
        assert user_resource["name"] == "YNAB User"
        assert "Authenticated user information" in user_resource["description"]
        assert user_resource["mimeType"] == "application/json"


class TestUserResourceRead:
    """Tests for reading user resource via MCP."""

    def test_resources_read_user(self, test_client, mock_settings):
        """Test reading the user resource via MCP resources/read."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "ynab://user"},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return valid JSON-RPC response
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        
        # The result should contain YNAB user data structure
        assert "result" in data
        # The actual structure depends on YNAB API response

    def test_resources_read_missing_uri(self, test_client):
        """Test that resources/read without uri returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32602  # Invalid params

    def test_resources_read_invalid_uri(self, test_client):
        """Test that resources/read with invalid uri returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "invalid://uri"},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # This should return an error since the URI is not recognized
        assert "error" in data


class TestUserToolCall:
    """Tests for user tool operations via MCP."""

    def test_tools_call_get_user(self, test_client, mock_settings):
        """Test calling the get_user tool via MCP tools/call."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_user"
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return valid JSON-RPC response
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        
        # The result should contain user data
        assert "result" in data

    def test_tools_call_unknown_tool(self, test_client):
        """Test calling an unknown tool returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "nonexistent_tool"
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
