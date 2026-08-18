"""FastAPI application factory and middleware configuration."""

from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from directors_rag.api.routes import chat, evaluations, health, sources
from directors_rag.api.security import InMemoryRateLimitMiddleware, SecurityHeadersMiddleware
from directors_rag.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Construct the HTTP application without making network connections."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Citation-first educational RAG for filmmaking direction.",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.app_allowed_hosts)
    application.add_middleware(InMemoryRateLimitMiddleware, requests_per_minute=60)
    application.add_middleware(SecurityHeadersMiddleware)
    application.include_router(health.router)
    application.include_router(chat.router)
    application.include_router(sources.router)
    application.include_router(evaluations.router)

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        incident_id = str(uuid.uuid4())
        logger.exception("Unhandled error incident_id=%s path=%s", incident_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Unexpected server error", "incident_id": incident_id},
        )

    return application


app = create_app()
