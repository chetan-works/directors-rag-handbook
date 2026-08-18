"""Dependency-light, provenance-preserving recursive text chunking."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable

from directors_rag.domain.models import DocumentChunk, SourceDefinition, TextSection

_CHUNK_NAMESPACE = uuid.UUID("5c44c665-7f38-4682-bf5a-74ebc39f98ee")


class TextChunker:
    """Split sections on paragraph boundaries with a bounded character overlap."""

    def __init__(self, chunk_size: int = 1_200, overlap: int = 180) -> None:
        if chunk_size < 200 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("chunk_size must be >= 200 and overlap must be smaller")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def chunk(
        self,
        source: SourceDefinition,
        sections: Iterable[TextSection],
        content_sha256: str,
    ) -> list[DocumentChunk]:
        """Create deterministic chunks so re-ingestion safely replaces points."""
        chunks: list[DocumentChunk] = []
        for section in sections:
            for text in self._split(section.text):
                index = len(chunks)
                stable_key = f"{source.id}:{content_sha256}:{index}"
                chunks.append(
                    DocumentChunk(
                        id=str(uuid.uuid5(_CHUNK_NAMESPACE, stable_key)),
                        source_id=source.id,
                        source_title=source.title,
                        source_url=str(source.attribution_url),
                        license=source.license,
                        text=text,
                        chunk_index=index,
                        heading=section.heading,
                        page=section.page,
                        content_sha256=content_sha256,
                    )
                )
        return chunks

    def _split(self, text: str) -> list[str]:
        paragraphs = [" ".join(item.split()) for item in text.split("\n") if item.strip()]
        output: list[str] = []
        current = ""
        for paragraph in paragraphs:
            pieces = self._hard_split(paragraph)
            for piece in pieces:
                candidate = f"{current}\n\n{piece}".strip() if current else piece
                if len(candidate) <= self._chunk_size:
                    current = candidate
                    continue
                if current:
                    output.append(current)
                    prefix = current[-self._overlap :] if self._overlap else ""
                    current = f"{prefix} {piece}".strip()
                else:
                    output.append(piece)
        if current:
            output.append(current)
        return output

    def _hard_split(self, text: str) -> list[str]:
        if len(text) <= self._chunk_size:
            return [text]
        step = self._chunk_size - self._overlap
        return [text[start : start + self._chunk_size] for start in range(0, len(text), step)]


def sha256_hex(content: bytes) -> str:
    """Return a stable lowercase SHA-256 digest."""
    return hashlib.sha256(content).hexdigest()
