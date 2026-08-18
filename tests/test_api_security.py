"""API authentication tests without external infrastructure."""

import pytest
from httpx import ASGITransport, AsyncClient

from directors_rag.api.main import app
from directors_rag.config import get_settings


@pytest.mark.asyncio
async def test_liveness_is_public_and_hardened() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


@pytest.mark.asyncio
async def test_source_catalog_requires_api_key() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/sources")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_source_catalog_accepts_configured_api_key() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/sources",
            headers={"X-API-Key": get_settings().app_api_key},
        )
    assert response.status_code == 200
