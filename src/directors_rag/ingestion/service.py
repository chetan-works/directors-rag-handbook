"""Application service coordinating source ingestion."""

from __future__ import annotations

import asyncio

from directors_rag.domain.models import IngestionResult, SourceDefinition
from directors_rag.ingestion.chunking import TextChunker, sha256_hex
from directors_rag.ingestion.loaders import CuratedSourceLoader
from directors_rag.retrieval.embeddings import FastEmbedder
from directors_rag.retrieval.vector_store import QdrantVectorStore
from directors_rag.storage.minio_store import MinioDocumentStore


class IngestionService:
    """Archive a raw source in MinIO and index its normalized chunks in Qdrant."""

    def __init__(
        self,
        loader: CuratedSourceLoader,
        chunker: TextChunker,
        embedder: FastEmbedder,
        vector_store: QdrantVectorStore,
        document_store: MinioDocumentStore,
    ) -> None:
        self._loader = loader
        self._chunker = chunker
        self._embedder = embedder
        self._vectors = vector_store
        self._documents = document_store

    async def ingest(self, source: SourceDefinition) -> IngestionResult:
        """Ingest one source while keeping blocking SDK work off the event loop."""
        loaded = await self._loader.load(source)
        digest = sha256_hex(loaded.content)
        suffix = "pdf" if loaded.content_type == "application/pdf" else "html"
        object_key = f"raw/{source.id}/{digest}.{suffix}"
        chunks = self._chunker.chunk(source, loaded.sections, digest)
        if not chunks:
            raise ValueError("No non-empty chunks were produced")

        await asyncio.to_thread(
            self._documents.put_bytes,
            object_key,
            loaded.content,
            loaded.content_type,
        )
        vectors = await asyncio.to_thread(self._embedder.embed, [item.text for item in chunks])
        await asyncio.to_thread(self._vectors.upsert, chunks, vectors)
        return IngestionResult(
            source_id=source.id,
            chunks_indexed=len(chunks),
            object_key=object_key,
            content_sha256=digest,
        )
