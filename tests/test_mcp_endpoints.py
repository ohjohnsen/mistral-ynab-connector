"""Tests for the MCP JSON-RPC POST endpoint at /mcp."""

import pytest


class TestMCPEndpointBasics:
    """Basic tests for the /mcp endpoint."""

    def test_post_mcp_requires_json(self, test_client):
        """Test that POST /mcp requires valid JSON."""
        response = test_client.post("/mcp", content="not json")
        
        assert response.status_code == 400
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid JSON

    def test_post_mcp_missing_method(self, test_client):
        """Test that missing method returns error."""
        response = test_client.post("/mcp", json={"jsonrpc": "2.0", "id": 1})
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found

    def test_post_mcp_invalid_method(self, test_client):
        """Test that invalid method returns error."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "nonexistent_method", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method not found


class TestMCPInitialize:
    """Tests for the initialize method."""

    def test_initialize_returns_capabilities(self, test_client):
        """Test that initialize returns server capabilities."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "initialize", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert data["id"] == 1
        
        result = data["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "tools" in result["capabilities"]
        assert "resources" in result["capabilities"]

    def test_initialize_with_params(self, test_client):
        """Test initialize with client parameters."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "Test Client",
                        "version": "1.0.0"
                    }
                },
                "id": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert data["id"] == 2


class TestMCPToolsList:
    """Tests for the tools/list method."""

    def test_tools_list_returns_tools(self, test_client):
        """Test that tools/list returns available tools."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "tools" in data["result"]
        
        tools = data["result"]["tools"]
        assert len(tools) > 0
        
        # Check that each tool has required fields
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_tools_list_includes_user_tools(self, test_client):
        """Test that tools/list includes user-related tools."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        
        data = response.json()
        tools = data["result"]["tools"]
        
        tool_names = [tool["name"] for tool in tools]
        assert "get_user" in tool_names


class TestMCPResourcesList:
    """Tests for the resources/list method."""

    def test_resources_list_returns_resources(self, test_client, mock_settings, mock_ynab_client):
        """Test that resources/list returns available resources."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "resources" in data["result"]
        
        resources = data["result"]["resources"]
        assert len(resources) > 0
        
        # Check that each resource has required fields
        for resource in resources:
            assert "uri" in resource
            assert "name" in resource
            assert "description" in resource
            assert "mimeType" in resource

    def test_resources_list_includes_user(self, test_client, mock_settings, mock_ynab_client):
        """Test that resources/list includes the user resource."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        uris = [r["uri"] for r in resources]
        assert "ynab://user" in uris
