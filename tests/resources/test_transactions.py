"""Tests for transaction resource operations via MCP endpoint."""

import pytest


class TestTransactionsResourceList:
    """Tests for listing transaction resources."""

    def test_resources_list_includes_transactions_template(self, test_client):
        """Test that server-card includes the transactions resource template."""
        response = test_client.get("/.well-known/mcp/server-card")
        
        assert response.status_code == 200
        data = response.json()
        
        resource_templates = data.get("hints", {}).get("resourceTemplates", [])
        uris = [rt["uriTemplate"] for rt in resource_templates]
        
        assert "ynab://plan/{plan_id}/transactions" in uris

    def test_resources_list_includes_transaction_resources(self, test_client, mock_ynab_client):
        """Test that resources/list includes transaction resources."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        resources = data["result"]["resources"]
        
        uris = [r["uri"] for r in resources]
        # Should have at least one transaction resource
        transaction_uris = [u for u in uris if "/transactions" in u]
        assert len(transaction_uris) >= 1

    def test_transaction_resource_has_correct_fields(self, test_client, mock_ynab_client):
        """Test that transaction resources have correct metadata."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "resources/list", "id": 1}
        )
        
        data = response.json()
        resources = data["result"]["resources"]
        
        # Find a transaction resource
        transaction_resource = next(
            (r for r in resources if "/transactions" in r["uri"] and "/scheduled" not in r["uri"]),
            None
        )
        
        assert transaction_resource is not None
        assert "name" in transaction_resource
        assert "Transactions:" in transaction_resource["name"]
        assert "description" in transaction_resource
        assert "Transactions for plan" in transaction_resource["description"]
        assert transaction_resource["mimeType"] == "application/json"


class TestTransactionsToolCall:
    """Tests for transaction tool operations via MCP."""

    def test_tools_list_includes_transaction_tools(self, test_client):
        """Test that tools/list includes transaction-related tools."""
        response = test_client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        )
        
        data = response.json()
        tools = data["result"]["tools"]
        
        tool_names = [tool["name"] for tool in tools]
        assert "get_transactions" in tool_names

    def test_tools_call_get_transactions(self, test_client, mock_ynab_client):
        """Test calling the get_transactions tool via MCP tools/call."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
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


class TestTransactionsDateValidation:
    """Tests for date parameter validation in get_transactions."""

    def test_valid_date_format(self, test_client, mock_ynab_client):
        """Test that valid YYYY-MM-DD date format is accepted."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "since_date": "2024-01-15",
                        "until_date": "2024-01-31"
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        # Should succeed with valid dates
        assert "result" in data

    def test_invalid_date_format(self, test_client, mock_ynab_client):
        """Test that invalid date format returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "since_date": "15-01-2024"  # Wrong format
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "error" in data
        assert "since_date must be in YYYY-MM-DD format" in data["error"]["message"]

    def test_invalid_date_not_a_date(self, test_client, mock_ynab_client):
        """Test that non-date string returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "since_date": "not-a-date"
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "YYYY-MM-DD" in data["error"]["message"]

    def test_invalid_date_february_30(self, test_client, mock_ynab_client):
        """Test that invalid calendar date returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "since_date": "2024-02-30"  # Invalid date
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "not a valid date" in data["error"]["message"]

    def test_date_with_type_filter(self, test_client, mock_ynab_client):
        """Test date filtering combined with type filter."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "since_date": "2024-01-01",
                        "until_date": "2024-01-31",
                        "type": "uncategorized"
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data


class TestTransactionsPagination:
    """Tests for pagination in get_transactions."""

    def test_pagination_with_limit(self, test_client, mock_ynab_client):
        """Test that limit parameter works."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "limit": 10
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_pagination_with_limit_and_offset(self, test_client, mock_ynab_client):
        """Test that limit and offset parameters work together."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "limit": 25,
                        "offset": 10
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_invalid_limit_negative(self, test_client, mock_ynab_client):
        """Test that negative limit returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "limit": -5
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "limit must be a positive integer" in data["error"]["message"]

    def test_invalid_limit_zero(self, test_client, mock_ynab_client):
        """Test that zero limit returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "limit": 0
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "limit must be a positive integer" in data["error"]["message"]

    def test_invalid_limit_not_integer(self, test_client, mock_ynab_client):
        """Test that non-integer limit returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "limit": "not-a-number"
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "limit must be a positive integer" in data["error"]["message"]

    def test_invalid_offset_negative(self, test_client, mock_ynab_client):
        """Test that negative offset returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {
                        "plan_id": "test-plan-id-001",
                        "offset": -1
                    }
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "offset must be a non-negative integer" in data["error"]["message"]

    def test_missing_plan_id(self, test_client):
        """Test that missing plan_id returns error."""
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transactions",
                    "arguments": {}
                },
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "plan_id is required" in data["error"]["message"]


class TestTransactionsResourceRead:
    """Tests for reading transaction resources via MCP."""

    def test_resources_read_plan_transactions(self, test_client, mock_ynab_client):
        """Test reading transactions for a specific plan."""
        plan_id = "test-plan-id-001"
        transactions_uri = f"ynab://plan/{plan_id}/transactions"
        
        response = test_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "resources/read",
                "params": {"uri": transactions_uri},
                "id": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
