"""Tests for deterministic, bounded chunk construction."""

from directors_rag.domain.models import SourceDefinition, SourceKind, TextSection
from directors_rag.ingestion.chunking import TextChunker, sha256_hex


def source() -> SourceDefinition:
    """Return a small valid source definition."""
    return SourceDefinition(
        id="test-source",
        title="Test",
        author="Test Author",
        url="https://example.com/article",
        kind=SourceKind.HTML,
        license="CC BY 4.0",
        attribution_url="https://example.com/article",
    )


def test_chunks_are_deterministic_and_keep_provenance() -> None:
    chunker = TextChunker(chunk_size=220, overlap=20)
    sections = [TextSection(heading="Blocking", text=("Action reveals character. " * 30))]
    first = chunker.chunk(source(), sections, "abc123")
    second = chunker.chunk(source(), sections, "abc123")

    assert [item.id for item in first] == [item.id for item in second]
    assert all(item.source_id == "test-source" for item in first)
    assert all(item.heading == "Blocking" for item in first)
    assert all(item.text for item in first)


def test_sha256_is_stable() -> None:
    assert sha256_hex(b"film") == "d0607f7ad2628b2af9158dfba06ce87166e66b15bf68f8f358f9aa27ccb7c321"
