"""Tests for HTML normalization and loader safety checks."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from directors_rag.domain.models import SourceDefinition, SourceKind
from directors_rag.ingestion.loaders import CuratedSourceLoader


def source(url: str = "https://example.com/article") -> SourceDefinition:
    """Return a reviewed HTML source definition."""
    return SourceDefinition(
        id="source-one",
        title="Source",
        author="Author",
        url=url,
        kind=SourceKind.HTML,
        license="CC BY 4.0",
        attribution_url=url,
    )


def test_html_extraction_keeps_article_and_drops_navigation() -> None:
    html = b"""
    <html><body><nav>This navigation sentence should disappear entirely.</nav>
    <article><h1>Blocking</h1><p>Blocking places performers in meaningful relationships.</p>
    <script>Ignore this unsafe script content completely.</script></article></body></html>
    """
    sections = CuratedSourceLoader._extract_html(html)
    assert sections[0].heading == "Blocking"
    assert "meaningful relationships" in sections[0].text
    assert "navigation" not in sections[0].text


@pytest.mark.asyncio
@respx.mock
async def test_loader_rejects_cross_host_redirect() -> None:
    respx.get("https://example.com/article").mock(
        return_value=Response(302, headers={"location": "https://internal.example/secret"})
    )
    with pytest.raises(ValueError, match="Cross-host"):
        await CuratedSourceLoader(1_000).load(source())


@pytest.mark.asyncio
@respx.mock
async def test_loader_rejects_oversized_response() -> None:
    respx.get("https://example.com/article").mock(
        return_value=Response(200, content=b"x" * 101, headers={"content-type": "text/html"})
    )
    with pytest.raises(ValueError, match="exceeds"):
        await CuratedSourceLoader(100).load(source())
