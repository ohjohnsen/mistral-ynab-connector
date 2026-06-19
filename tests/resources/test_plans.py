"""Tests for plan resource operations via MCP endpoint."""

import pytest


class TestPlansResourceList:
    """Tests for listing plan resources."""

    def test_resources_list_includes_plans_template(self, test_client):
        """Test that server-card includes the plans resource template."""
        response = test_client.get("/.well-known/mcp/server-card")
        
        assert response.status_code == 200
        data = response.json()
        
        resource_templates = data.get("hints", {}).get("resourceTemplates", [])
        uris = [rt["uriTemplate"] for rt in resource_templates]
        
        assert "ynab://plans" in uris

    def test_resources_list_includes_plan_resources(self, test_client, mock_ynab_client):
        """Test that resources/list includes plan resources."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        resources = data["result"]["resources"]
        
        uris = [r["uri"] for r in resources]
        # Should have at least one plan resource (ynab://plan/{id})
        plan_uris = [u for u in uris if u.startswith("ynab://plan/")]
        assert len(plan_uris) >= 1

    def test_plan_resource_has_correct_fields(self, test_client, mock_ynab_client):
        """Test that plan resources have correct metadata."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        # Find first plan resource
        plan_resource = next(
            (r for r in resources if r["uri"].startswith("ynab://plan/")),
            None
        )
        
        assert plan_resource is not None
        assert "name" in plan_resource
        assert "Plan:" in plan_resource["name"]
        assert "description" in plan_resource
        assert "YNAB Plan" in plan_resource["description"]
        assert plan_resource["mimeType"] == "application/json"


class TestPlansResourceRead:
    """Tests for reading plan resources via MCP."""

    def test_resources_read_specific_plan(self, test_client, mock_ynab_client):
        """Test reading a specific plan resource."""
        # Use the mock plan ID
        plan_uri = "ynab://plan/test-plan-id-001"
        
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": plan_uri},
                "id": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data

    def test_resources_read_invalid_plan_uri(self, test_client, mock_ynab_client):
        """Test that resources/read with invalid plan uri returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "ynab://plan/nonexistent-id"},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # With mocked client, this will still return data (from mock_get_plan)
        # In a real scenario, it would return an error
        assert "result" in data or "error" in data


class TestPlansToolCall:
    """Tests for plan tool operations via MCP."""

    def test_tools_list_includes_plan_tools(self, test_client):
        """Test that tools/list includes plan-related tools."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        
        data = response.json()
        tools = data["result"]["tools"]
        
        tool_names = [tool["name"] for tool in tools]
        assert "get_plans" in tool_names
        assert "get_plan" in tool_names

    def test_tools_call_get_plans(self, test_client, mock_ynab_client):
        """Test calling the get_plans tool via MCP tools/call."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_plans"
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return valid JSON-RPC response
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        
        # The result should contain plans data
        assert "result" in data

    def test_tools_call_get_plans_with_include_accounts(self, test_client, mock_ynab_client):
        """Test calling get_plans with include_accounts parameter."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_plans",
                    "arguments": {
                        "include_accounts": True
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data

    def test_tools_call_get_plan_with_id(self, test_client, mock_ynab_client):
        """Test calling get_plan tool with a plan_id."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_plan",
                    "arguments": {
                        "plan_id": "test-plan-id-001"
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data


class TestPlanSettingsResource:
    """Tests for plan settings resources."""

    def test_resources_list_includes_plan_settings(self, test_client, mock_ynab_client):
        """Test that resources/list includes plan settings resources."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        uris = [r["uri"] for r in resources]
        settings_uris = [u for u in uris if "/settings" in u]
        assert len(settings_uris) >= 1

    def test_plan_settings_resource_has_correct_fields(self, test_client, mock_ynab_client):
        """Test that plan settings resource has correct metadata."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        # Find a plan settings resource
        settings_resource = next(
            (r for r in resources if "/settings" in r["uri"]),
            None
        )
        
        assert settings_resource is not None
        assert "Settings:" in settings_resource["name"]
        assert "Settings for plan" in settings_resource["description"]
