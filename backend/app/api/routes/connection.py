"""AWS Bedrock connection test endpoint."""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.requests import ConnectionTestRequest
from app.models.responses import ConnectionTestResponse

router = APIRouter()


@router.post(
    "/connection/test",
    response_model=ConnectionTestResponse,
)
async def test_connection(request: Optional[ConnectionTestRequest] = None):
    """
    Test connection to AWS Bedrock.

    Validates credentials and model access.
    """
    region = (request.region if request else None) or settings.aws_region
    model_id = (request.model_id if request else None) or settings.bedrock_model_id

    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError, NoCredentialsError

        # Configure boto3 with timeout
        config = Config(
            connect_timeout=10,
            read_timeout=30,
            retries={"max_attempts": 2},
        )

        # Create bedrock client
        start_time = time.time()

        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=config,
        )

        # Test with a minimal invoke to validate credentials and model access
        test_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10,
            "messages": [{"role": "user", "content": "Hi"}],
        }

        import json

        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(test_body),
            contentType="application/json",
            accept="application/json",
        )

        latency_ms = (time.time() - start_time) * 1000

        return ConnectionTestResponse(
            success=True,
            region=region,
            model_id=model_id,
            message="Successfully connected to AWS Bedrock",
            latency_ms=round(latency_ms, 2),
        )

    except NoCredentialsError:
        return ConnectionTestResponse(
            success=False,
            region=region,
            model_id=model_id,
            message="AWS credentials not found",
            error="No valid AWS credentials found. Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY or use IAM roles.",
        )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        if error_code == "AccessDeniedException":
            return ConnectionTestResponse(
                success=False,
                region=region,
                model_id=model_id,
                message="Access denied to Bedrock",
                error=f"IAM permissions error: {error_message}",
            )
        elif error_code == "ValidationException":
            return ConnectionTestResponse(
                success=False,
                region=region,
                model_id=model_id,
                message="Invalid model configuration",
                error=f"Model validation failed: {error_message}",
            )
        else:
            return ConnectionTestResponse(
                success=False,
                region=region,
                model_id=model_id,
                message=f"AWS error: {error_code}",
                error=error_message,
            )
    except ImportError:
        return ConnectionTestResponse(
            success=False,
            region=region,
            model_id=model_id,
            message="boto3 not installed",
            error="AWS SDK (boto3) is not installed",
        )
    except Exception as e:
        return ConnectionTestResponse(
            success=False,
            region=region,
            model_id=model_id,
            message="Connection test failed",
            error=str(e),
        )
