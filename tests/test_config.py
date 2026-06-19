"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch

from config import Settings, settings


class TestSettingsInitialization:
    """Tests for Settings class initialization."""

    def test_default_settings(self):
        """Test that default settings are initialized correctly."""
        # Use _env_file=None to prevent loading .env
        config = Settings(_env_file=None)
        
        assert config.ynab_api_key == ""
        assert config.ynab_api_url == "https://api.ynab.com/v1"
        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8000
        assert config.mcp_name == "YNAB Connector"
        assert config.mcp_version == "0.1.0"

    def test_custom_settings(self):
        """Test that custom settings override defaults."""
        config = Settings(
            ynab_api_key="custom_key",
            ynab_api_url="https://custom.api.url/v1",
            server_host="127.0.0.1",
            server_port=9000,
            mcp_name="Custom Connector",
            mcp_version="2.0.0"
        )
        
        assert config.ynab_api_key == "custom_key"
        assert config.ynab_api_url == "https://custom.api.url/v1"
        assert config.server_host == "127.0.0.1"
        assert config.server_port == 9000
        assert config.mcp_name == "Custom Connector"
        assert config.mcp_version == "2.0.0"

    def test_settings_from_env_file(self, tmp_path):
        """Test that settings are loaded from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("YNAB_API_KEY=env_test_key\nYNAB_API_URL=https://env.api.url/v1\n")
        
        config = Settings(_env_file=str(env_file))
        
        assert config.ynab_api_key == "env_test_key"
        assert config.ynab_api_url == "https://env.api.url/v1"

    def test_settings_from_environment_variables(self):
        """Test that settings are loaded from environment variables."""
        with patch.dict(
            os.environ,
            {
                "YNAB_API_KEY": "os_test_key",
                "YNAB_API_URL": "https://os.api.url/v1",
                "SERVER_HOST": "0.0.0.0",
                "SERVER_PORT": "9999",
            }
        ):
            # Use _env_file=None to prevent loading .env, only use os.environ
            config = Settings(_env_file=None)
            
            assert config.ynab_api_key == "os_test_key"
            assert config.ynab_api_url == "https://os.api.url/v1"
            assert config.server_port == 9999


class TestSettingsHeaders:
    """Tests for the ynab_headers property."""

    def test_ynab_headers_with_api_key(self):
        """Test that headers are generated correctly with API key."""
        config = Settings(ynab_api_key="test_api_key_123")
        headers = config.ynab_headers
        
        assert isinstance(headers, dict)
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_key_123"
        assert headers["Content-Type"] == "application/json"

    def test_ynab_headers_with_empty_api_key(self):
        """Test that headers are generated with empty API key."""
        config = Settings(_env_file=None, ynab_api_key="")
        headers = config.ynab_headers
        
        assert headers["Authorization"] == "Bearer "
        assert headers["Content-Type"] == "application/json"


class TestGlobalSettingsInstance:
    """Tests for the global settings instance."""

    def test_global_settings_exists(self):
        """Test that the global settings instance exists."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_global_settings_has_expected_attributes(self):
        """Test that the global settings instance has expected attributes."""
        assert hasattr(settings, "ynab_api_key")
        assert hasattr(settings, "ynab_api_url")
        assert hasattr(settings, "server_host")
        assert hasattr(settings, "server_port")
        assert hasattr(settings, "mcp_name")
        assert hasattr(settings, "mcp_version")
