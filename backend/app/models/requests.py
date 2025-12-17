"""API request models with validation."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    """Request to start compliance analysis."""

    session_id: str = Field(..., min_length=1, max_length=64)
    frameworks: list[str] = Field(
        default=["SOC2", "ISO27001", "NIST_CSF"],
        description="Compliance frameworks to analyze against",
    )

    @field_validator("frameworks")
    @classmethod
    def validate_frameworks(cls, v: list[str]) -> list[str]:
        valid_frameworks = {
            "SOC2",
            "ISO27001",
            "NIST_CSF",
            "HIPAA",
            "GDPR",
            "PCI_DSS",
        }
        for framework in v:
            if framework not in valid_frameworks:
                raise ValueError(f"Invalid framework: {framework}")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        # Only allow alphanumeric and hyphens
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("Session ID must be alphanumeric with hyphens only")
        return v


class ChatRequest(BaseModel):
    """Request for chat message."""

    session_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=10000)
    include_context: bool = Field(
        default=True, description="Include analysis results as context"
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("Session ID must be alphanumeric with hyphens only")
        return v

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        # Basic sanitization - remove null bytes and control characters
        return "".join(c for c in v if c.isprintable() or c in "\n\t")


class ConnectionTestRequest(BaseModel):
    """Request to test AWS Bedrock connection."""

    region: Optional[str] = Field(default=None, max_length=32)
    model_id: Optional[str] = Field(default=None, max_length=128)

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            valid_regions = {
                "us-east-1",
                "us-west-2",
                "eu-west-1",
                "ap-northeast-1",
            }
            if v not in valid_regions:
                raise ValueError(f"Invalid AWS region: {v}")
        return v

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.startswith("anthropic.claude"):
            raise ValueError("Only Claude models are supported")
        return v
