"""Local, open-source text embeddings powered by FastEmbed/ONNX."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cached_property
from typing import Any


class FastEmbedder:
    """Lazily load a FastEmbed model and expose plain Python vectors."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    @cached_property
    def _model(self) -> Any:
        # Import lazily so API startup and lightweight unit tests stay fast.
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=self.model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a non-empty sequence of texts."""
        if not texts:
            return []
        return [vector.tolist() for vector in self._model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
        return self.embed([text])[0]
