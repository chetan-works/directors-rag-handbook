"""Liveness and dependency-readiness endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from directors_rag.api.dependencies import document_store, llm_client, vector_store

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str
    dependencies: dict[str, bool] | None = None


@router.get("/health/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    """Confirm that the API process is running."""
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    """Check MinIO, Qdrant, and the configured Ollama model."""
    minio_ok, qdrant_ok = await asyncio.gather(
        asyncio.to_thread(document_store().is_ready),
        asyncio.to_thread(vector_store().is_ready),
    )
    ollama_ok = await llm_client().is_ready()
    dependencies = {"minio": minio_ok, "qdrant": qdrant_ok, "ollama_model": ollama_ok}
    return HealthResponse(
        status="ready" if all(dependencies.values()) else "degraded",
        dependencies=dependencies,
    )
