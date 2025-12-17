"""Backend configuration with security defaults."""

import os
import secrets
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with secure defaults."""

    # Application
    app_name: str = "Vendor Security Analyzer"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"

    # CORS - restrict in production
    cors_origins: list[str] = Field(default=["http://localhost:3001"])
    cors_allow_credentials: bool = True

    # Security
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    session_ttl_hours: int = 24
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # File Upload Security
    upload_dir: Path = Field(default=Path("/tmp/analyzer-uploads"))
    max_file_size_mb: int = 100
    max_total_size_mb: int = 500
    allowed_extensions: set[str] = Field(
        default={".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt", ".md"}
    )
    allowed_mime_types: set[str] = Field(
        default={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "text/csv",
            "text/plain",
            "text/markdown",
        }
    )

    # AWS Configuration
    aws_region: str = Field(default="us-east-1")
    aws_role_arn: Optional[str] = Field(default=None)

    # Bedrock Configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    bedrock_max_tokens: int = 4096
    bedrock_temperature: float = 0.3
    bedrock_timeout: int = 60

    # Compliance Analyzer Path
    analyzer_package_path: Optional[str] = Field(default=None)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_total_size_bytes(self) -> int:
        return self.max_total_size_mb * 1024 * 1024


settings = Settings()
