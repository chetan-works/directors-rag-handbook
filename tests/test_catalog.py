"""Tests for the checked-in source manifest."""

from pathlib import Path

from directors_rag.ingestion.catalog import SourceCatalog


def test_catalog_is_valid_and_uses_https() -> None:
    sources = SourceCatalog(Path("data/sources.yaml")).all()
    assert len(sources) >= 5
    assert len({source.id for source in sources}) == len(sources)
    assert all(str(source.url).startswith("https://") for source in sources)
    assert all(source.license.startswith("CC ") for source in sources)
