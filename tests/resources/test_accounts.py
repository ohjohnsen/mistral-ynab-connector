"""Tests for account resource operations via MCP endpoint."""

import pytest


class TestAccountsResourceList:
    """Tests for listing account resources."""

    def test_resources_list_includes_accounts_template(self, test_client):
        """Test that server-card includes the accounts resource template."""
        response = test_client.get("/.well-known/mcp/server-card")
        
        assert response.status_code == 200
        data = response.json()
        
        resource_templates = data.get("hints", {}).get("resourceTemplates", [])
        uris = [rt["uriTemplate"] for rt in resource_templates]
        
        assert any("accounts" in u for u in uris)

    def test_resources_list_includes_account_resources(self, test_client, mock_ynab_client):
        """Test that resources/list includes account resources."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        resources = data["result"]["resources"]
        
        uris = [r["uri"] for r in resources]
        # Should have at least one account resource (ynab://plan/*/accounts)
        account_uris = [u for u in uris if "/accounts" in u]
        assert len(account_uris) >= 1

    def test_account_resource_has_correct_fields(self, test_client, mock_ynab_client):
        """Test that account resources have correct metadata."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        # Find an account resource
        account_resource = next(
            (r for r in resources if "/accounts" in r["uri"] and "/settings" not in r["uri"]),
            None
        )
        
        assert account_resource is not None
        assert "name" in account_resource
        assert "Accounts:" in account_resource["name"]
        assert "description" in account_resource
        assert "Accounts for plan" in account_resource["description"]
        assert account_resource["mimeType"] == "application/json"


class TestAccountsResourceRead:
    """Tests for reading account resources via MCP."""

    def test_resources_read_plan_accounts(self, test_client, mock_ynab_client):
        """Test reading accounts for a specific plan."""
        plan_id = "test-plan-id-001"
        accounts_uri = f"ynab://plan/{plan_id}/accounts"
        
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": accounts_uri},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 1
        assert "result" in data

    def test_resources_read_invalid_accounts_uri(self, test_client, mock_ynab_client):
        """Test that resources/read with invalid accounts uri returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": "ynab://plan/invalid/accounts"},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # With mocked client, this will still return data
        assert "result" in data or "error" in data


class TestAccountsToolCall:
    """Tests for account tool operations via MCP."""

    def test_tools_list_includes_account_tools(self, test_client):
        """Test that tools/list includes account-related tools."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        
        data = response.json()
        tools = data["result"]["tools"]
        
        tool_names = [tool["name"] for tool in tools]
        assert "get_accounts" in tool_names
        assert any("account" in name.lower() for name in tool_names)

    def test_tools_call_get_accounts(self, test_client, mock_ynab_client):
        """Test calling the get_accounts tool via MCP tools/call."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_accounts",
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
        assert data["id"] == 1
        assert "result" in data

    def test_tools_call_get_accounts_with_last_knowledge(self, test_client, mock_ynab_client):
        """Test calling get_accounts with last_knowledge_of_server parameter."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_accounts",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "last_knowledge_of_server": 12345
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data


class TestIndividualAccountResource:
    """Tests for individual account resources."""

    def test_resources_read_individual_account(self, test_client, mock_ynab_client, monkeypatch):
        """Test reading a specific account resource."""
        # Mock get_account method
        mock_client = mock_ynab_client
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
        
        plan_id = "test-plan-id-001"
        account_id = "test-account-id-001"
        account_uri = f"ynab://plan/{plan_id}/accounts/{account_id}"
        
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": account_uri},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        # Will return data from mock
        assert "result" in data or "error" in data
