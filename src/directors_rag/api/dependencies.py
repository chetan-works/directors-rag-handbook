"""Dependency graph shared by API routes."""

from __future__ import annotations

from functools import lru_cache

from directors_rag.config import get_settings
from directors_rag.evaluation.harness import EvaluationHarness
from directors_rag.ingestion.catalog import SourceCatalog
from directors_rag.ingestion.chunking import TextChunker
from directors_rag.ingestion.loaders import CuratedSourceLoader
from directors_rag.ingestion.service import IngestionService
from directors_rag.rag.llm import OllamaChatClient
from directors_rag.rag.service import RagService
from directors_rag.retrieval.embeddings import FastEmbedder
from directors_rag.retrieval.vector_store import QdrantVectorStore
from directors_rag.storage.minio_store import MinioDocumentStore


@lru_cache
def source_catalog() -> SourceCatalog:
    """Return the source manifest repository."""
    return SourceCatalog(get_settings().source_manifest_path)


@lru_cache
def embedder() -> FastEmbedder:
    """Return the process-wide lazy embedding model."""
    return FastEmbedder(get_settings().embedding_model)


@lru_cache
def vector_store() -> QdrantVectorStore:
    """Return the Qdrant adapter."""
    settings = get_settings()
    return QdrantVectorStore(
        settings.qdrant_url,
        settings.qdrant_collection,
        settings.embedding_dimension,
    )


@lru_cache
def document_store() -> MinioDocumentStore:
    """Return the MinIO adapter."""
    settings = get_settings()
    return MinioDocumentStore(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_bucket,
        secure=settings.minio_secure,
    )


@lru_cache
def llm_client() -> OllamaChatClient:
    """Return the Ollama adapter."""
    settings = get_settings()
    return OllamaChatClient(
        settings.ollama_url,
        settings.ollama_chat_model,
        settings.request_timeout_seconds,
    )


@lru_cache
def ingestion_service() -> IngestionService:
    """Return the fully wired ingestion application service."""
    settings = get_settings()
    return IngestionService(
        loader=CuratedSourceLoader(settings.max_upload_bytes),
        chunker=TextChunker(settings.chunk_size, settings.chunk_overlap),
        embedder=embedder(),
        vector_store=vector_store(),
        document_store=document_store(),
    )


@lru_cache
def rag_service() -> RagService:
    """Return the fully wired RAG application service."""
    settings = get_settings()
    return RagService(
        embedder(),
        vector_store(),
        llm_client(),
        default_top_k=settings.retrieval_top_k,
        relevance_threshold=settings.relevance_threshold,
    )


@lru_cache
def evaluation_harness() -> EvaluationHarness:
    """Return the golden-dataset evaluation harness."""
    settings = get_settings()
    return EvaluationHarness(rag_service(), settings.eval_dataset_path)
