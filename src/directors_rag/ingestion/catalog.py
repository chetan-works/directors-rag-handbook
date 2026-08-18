"""Load and validate the allowlisted source catalog."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import TypeAdapter

from directors_rag.domain.models import SourceDefinition


class SourceCatalog:
    """Read source metadata from the version-controlled YAML manifest."""

    def __init__(self, manifest_path: Path) -> None:
        self._manifest_path = manifest_path

    def all(self) -> list[SourceDefinition]:
        """Return every validated source in manifest order."""
        with self._manifest_path.open(encoding="utf-8") as handle:
            document = yaml.safe_load(handle) or {}
        return TypeAdapter(list[SourceDefinition]).validate_python(document.get("sources", []))

    def enabled(self) -> list[SourceDefinition]:
        """Return only sources explicitly enabled for ingestion."""
        return [source for source in self.all() if source.enabled]

    def get(self, source_id: str) -> SourceDefinition:
        """Look up a source by stable identifier."""
        for source in self.all():
            if source.id == source_id:
                return source
        raise KeyError(f"Unknown source: {source_id}")
