"""Defensive HTTP, HTML, and PDF loaders for reviewed source URLs."""

from __future__ import annotations

import io
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from directors_rag.domain.models import SourceDefinition, SourceKind, TextSection


@dataclass(frozen=True)
class LoadedSource:
    """Raw bytes and normalized text extracted from one source."""

    content: bytes
    content_type: str
    sections: list[TextSection]


class CuratedSourceLoader:
    """Fetch sources from their exact manifest URLs with strict size limits."""

    def __init__(self, max_bytes: int, timeout_seconds: float = 30.0) -> None:
        self._max_bytes = max_bytes
        self._timeout = timeout_seconds

    async def load(self, source: SourceDefinition) -> LoadedSource:
        """Download and extract one already-reviewed catalog entry."""
        parsed = urlparse(str(source.url))
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Curated sources must use an absolute HTTPS URL")

        headers = {"User-Agent": "DirectorsRAGHandbook/0.1 (+educational OER indexer)"}
        async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
            response = await client.get(str(source.url), follow_redirects=False)
            if response.is_redirect:
                location = response.headers.get("location", "")
                target = response.url.join(location)
                if target.scheme != "https" or target.host != response.url.host:
                    raise ValueError("Cross-host source redirects are not allowed")
                response = await client.get(target, follow_redirects=False)
            response.raise_for_status()
            content = response.content

        if len(content) > self._max_bytes:
            raise ValueError(f"Source exceeds the {self._max_bytes}-byte ingestion limit")

        content_type = response.headers.get("content-type", "application/octet-stream").split(";")[
            0
        ]
        if source.kind is SourceKind.PDF:
            sections = self._extract_pdf(content)
            content_type = "application/pdf"
        else:
            sections = self._extract_html(content)
            content_type = "text/html"
        if not sections:
            raise ValueError("Source did not contain extractable text")
        return LoadedSource(content=content, content_type=content_type, sections=sections)

    @staticmethod
    def _extract_pdf(content: bytes) -> list[TextSection]:
        """Extract text while preserving PDF page numbers."""
        reader = PdfReader(io.BytesIO(content))
        return [
            TextSection(text=text, page=index, heading=f"Page {index}")
            for index, page in enumerate(reader.pages, start=1)
            if (text := (page.extract_text() or "").strip())
        ]

    @staticmethod
    def _extract_html(content: bytes) -> list[TextSection]:
        """Extract semantic sections from an article-like HTML document."""
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "form", "noscript", "svg"]):
            tag.decompose()
        root = soup.find("article") or soup.find("main") or soup.body or soup
        sections: list[TextSection] = []
        heading: str | None = None
        buffer: list[str] = []

        def flush() -> None:
            text = "\n\n".join(buffer).strip()
            if text:
                sections.append(TextSection(heading=heading, text=text))
            buffer.clear()

        for element in root.find_all(["h1", "h2", "h3", "p", "li"], recursive=True):
            text = " ".join(element.get_text(" ", strip=True).split())
            if not text:
                continue
            if element.name in {"h1", "h2", "h3"}:
                flush()
                heading = text
            elif len(text) >= 30:
                buffer.append(text)
        flush()
        return sections
