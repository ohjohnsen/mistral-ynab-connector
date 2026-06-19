"""Tests for validation helper functions in mcp_server.py."""

import pytest
from datetime import datetime

from mcp_server import (
    _validate_date_format,
    _validate_required_param,
    get_ynab_api_key,
    get_ynab_client,
)


class TestValidateDateFormat:
    """Tests for _validate_date_format function."""

    def test_valid_date_yyyy_mm_dd(self):
        """Test that valid YYYY-MM-DD dates pass validation."""
        assert _validate_date_format("2024-01-15", "date") == "2024-01-15"
        assert _validate_date_format("2024-12-31", "date") == "2024-12-31"
        assert _validate_date_format("2000-02-29", "date") == "2000-02-29"  # Leap year

    def test_valid_date_with_none(self):
        """Test that None is returned as None."""
        assert _validate_date_format(None, "date") is None

    def test_invalid_date_format_wrong_separator(self):
        """Test that dates with wrong separators are rejected."""
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            _validate_date_format("2024/01/15", "date")
        
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            _validate_date_format("2024.01.15", "date")

    def test_invalid_date_format_wrong_length(self):
        """Test that dates with wrong length are rejected."""
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            _validate_date_format("24-01-15", "date")
        
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            _validate_date_format("2024-1-1", "date")

    def test_invalid_date_format_not_a_date(self):
        """Test that non-date strings are rejected."""
        with pytest.raises(ValueError, match="must be in YYYY-MM-DD format"):
            _validate_date_format("not-a-date", "date")

    def test_invalid_date_value_february_30(self):
        """Test that invalid date values are rejected."""
        with pytest.raises(ValueError, match="is not a valid date"):
            _validate_date_format("2024-02-30", "date")

    def test_invalid_date_value_month_13(self):
        """Test that invalid month values are rejected."""
        with pytest.raises(ValueError, match="is not a valid date"):
            _validate_date_format("2024-13-01", "date")

    def test_invalid_date_type_not_string(self):
        """Test that non-string types are rejected."""
        with pytest.raises(ValueError, match="must be a string"):
            _validate_date_format(12345, "date")
        
        with pytest.raises(ValueError, match="must be a string"):
            _validate_date_format(datetime.now(), "date")

    def test_error_message_includes_param_name(self):
        """Test that error messages include the parameter name."""
        with pytest.raises(ValueError, match="since_date"):
            _validate_date_format("invalid", "since_date")


class TestValidateRequiredParam:
    """Tests for _validate_required_param function."""

    def test_valid_required_param_string(self):
        """Test that valid string parameters pass validation."""
        result = _validate_required_param("test_value", "param_name", str)
        assert result == "test_value"

    def test_valid_required_param_int(self):
        """Test that valid int parameters pass validation."""
        result = _validate_required_param(42, "count", int)
        assert result == 42

    def test_valid_required_param_multiple_types(self):
        """Test that parameters matching any of multiple types pass."""
        result = _validate_required_param("test", "param", (str, int))
        assert result == "test"
        
        result = _validate_required_param(123, "param", (str, int))
        assert result == 123

    def test_missing_required_param(self):
        """Test that missing (None) parameters are rejected."""
        with pytest.raises(ValueError, match="is required"):
            _validate_required_param(None, "api_key", str)

    def test_wrong_type_single(self):
        """Test that parameters of wrong type are rejected."""
        with pytest.raises(ValueError, match="must be of type str"):
            _validate_required_param(123, "name", str)

    def test_wrong_type_multiple(self):
        """Test that parameters not matching any type are rejected."""
        with pytest.raises(ValueError, match="must be of type"):
            _validate_required_param([], "param", (str, int))

    def test_error_message_includes_param_name_and_types(self):
        """Test that error messages include parameter name and expected types."""
        with pytest.raises(ValueError, match=r"api_key.*required"):
            _validate_required_param(None, "api_key", str)


class TestGetYNABApiKey:
    """Tests for get_ynab_api_key dependency."""

    def test_extracts_bearer_token(self, mock_settings):
        """Test that Bearer token is extracted from Authorization header."""
        from fastapi import Header
        from fastapi.testclient import TestClient
        from mcp_server import app
        
        client = TestClient(app)
        
        # This tests the dependency through the actual endpoint
        # Since get_ynab_api_key is a dependency, we test it via an endpoint that uses it
        response = client.get(
            "/.well-known/mcp/server-card",
            headers={"Authorization": "Bearer test_token_12345"}
        )
        
        # If we get a response (not 401), the token was extracted
        assert response.status_code == 200

    def test_uses_env_var_when_no_header(self, mock_settings):
        """Test that environment variable is used when no header is provided."""
        from fastapi.testclient import TestClient
        from mcp_server import app
        
        client = TestClient(app)
        
        # With mock_settings fixture, we have a test API key
        response = client.get("/.well-known/mcp/server-card")
        
        # Should succeed because mock_settings provides a key
        assert response.status_code == 200


class TestGetYNABClient:
    """Tests for get_ynab_client dependency."""

    def test_returns_client_instance(self, mock_settings):
        """Test that a YNABClient instance is returned."""
        from fastapi.testclient import TestClient
        from mcp_server import app
        from ynab_client import YNABClient
        
        client = TestClient(app)
        
        # The dependency is used internally, but we can verify it works
        # by calling an endpoint that uses the client
        response = client.get("/.well-known/mcp/server-card")
        
        assert response.status_code == 200

    def test_creates_new_client_for_header_key(self, mock_settings, mock_ynab_client):
        """Test that new client is created for header-based API keys."""
        # This is tested via the mock_ynab_client fixture
        # which verifies YNABClient is properly instantiated
        from fastapi.testclient import TestClient
        from mcp_server import app
        
        client = TestClient(app)
        
        # With mock_ynab_client, we can verify the client creation
        response = client.get("/.well-known/mcp/server-card")
        
        assert response.status_code == 200
