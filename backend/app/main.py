"""FastAPI application entry point with security configuration."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import analysis, chat, connection, export, upload
from app.api.websocket import handlers as ws_handlers
from app.config import settings

# Add the compliance analyzer to path if configured
if settings.analyzer_package_path:
    sys.path.insert(0, settings.analyzer_package_path)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > settings.max_file_size_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request body too large"},
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    print(f"Upload directory: {settings.upload_dir}")
    yield
    # Shutdown - cleanup could go here


app = FastAPI(
    title=settings.app_name,
    description="AI-powered vendor security compliance analyzer",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Include API routes
app.include_router(upload.router, prefix=settings.api_prefix, tags=["upload"])
app.include_router(analysis.router, prefix=settings.api_prefix, tags=["analysis"])
app.include_router(connection.router, prefix=settings.api_prefix, tags=["connection"])
app.include_router(export.router, prefix=settings.api_prefix, tags=["export"])
app.include_router(chat.router, prefix=settings.api_prefix, tags=["chat"])

# WebSocket routes
app.include_router(ws_handlers.router, tags=["websocket"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler - don't expose internals in production."""
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "type": type(exc).__name__},
        )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
