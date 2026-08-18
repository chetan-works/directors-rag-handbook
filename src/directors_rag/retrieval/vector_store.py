"""Qdrant vector-store adapter with domain-focused inputs and outputs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from qdrant_client import QdrantClient, models

from directors_rag.domain.models import DocumentChunk, RetrievedChunk


class QdrantVectorStore:
    """Persist embedded chunks and run cosine-similarity searches."""

    def __init__(self, url: str, collection: str, dimension: int) -> None:
        self._client = QdrantClient(url=url)
        self._collection = collection
        self._dimension = dimension

    def ensure_collection(self) -> None:
        """Create the configured collection if necessary."""
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=models.VectorParams(
                    size=self._dimension,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert(self, chunks: Sequence[DocumentChunk], vectors: Sequence[list[float]]) -> None:
        """Upsert chunks and matching vectors atomically in one batch."""
        if len(chunks) != len(vectors):
            raise ValueError("Every chunk must have exactly one embedding")
        if not chunks:
            return
        self.ensure_collection()
        points = [
            models.PointStruct(id=chunk.id, vector=vector, payload=chunk.model_dump())
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(collection_name=self._collection, points=points, wait=True)

    def search(self, vector: list[float], limit: int) -> list[RetrievedChunk]:
        """Return the most similar chunks with their cosine scores."""
        self.ensure_collection()
        result = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        chunks: list[RetrievedChunk] = []
        for point in result.points:
            payload: dict[str, Any] = dict(point.payload or {})
            chunks.append(RetrievedChunk(**payload, score=float(point.score)))
        return chunks

    def count(self) -> int:
        """Return the number of indexed chunks."""
        self.ensure_collection()
        return int(self._client.count(self._collection, exact=True).count)

    def is_ready(self) -> bool:
        """Return whether Qdrant can serve the configured collection."""
        try:
            self.ensure_collection()
        except Exception:  # readiness must collapse vendor-specific errors
            return False
        return True
