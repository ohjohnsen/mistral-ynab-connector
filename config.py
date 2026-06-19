"""Configuration management for YNAB MCP Connector."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # YNAB API Configuration
    ynab_api_key: str = ""
    ynab_api_url: str = "https://api.ynab.com/v1"

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # MCP Configuration
    mcp_name: str = "YNAB Connector"
    mcp_version: str = "0.1.0"

    @property
    def ynab_headers(self) -> dict[str, str]:
        """Generate headers for YNAB API requests."""
        return {
            "Authorization": f"Bearer {self.ynab_api_key}",
            "Content-Type": "application/json",
        }


# Global settings instance
settings = Settings()
