"""Validated domain models for the RAG application."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class SourceKind(StrEnum):
    """Supported curated source formats."""

    HTML = "html"
    PDF = "pdf"


class RagMode(StrEnum):
    """Retrieval-generation strategies exposed for educational comparison."""

    NAIVE = "naive"
    CITED = "cited"
    SELF_RAG = "self_rag"


class SourceDefinition(BaseModel):
    """A reviewed source that the ingestion service is allowed to fetch."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,63}$")
    title: str
    author: str
    url: HttpUrl
    kind: SourceKind
    license: str
    attribution_url: HttpUrl
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)


class TextSection(BaseModel):
    """A normalized section extracted from a source document."""

    heading: str | None = None
    text: str
    page: int | None = None


class DocumentChunk(BaseModel):
    """A retrieval unit with complete provenance metadata."""

    id: str
    source_id: str
    source_title: str
    source_url: str
    license: str
    text: str
    chunk_index: int
    heading: str | None = None
    page: int | None = None
    content_sha256: str


class RetrievedChunk(DocumentChunk):
    """A document chunk returned by vector search."""

    score: float = Field(ge=-1.0, le=1.0)


class Citation(BaseModel):
    """A source reference used by a generated answer."""

    number: int
    source_id: str
    title: str
    url: str
    excerpt: str
    page: int | None = None
    score: float


class TraceStep(BaseModel):
    """An inspectable stage in a RAG request."""

    stage: str
    detail: str
    values: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Question and strategy selected by an API client."""

    question: str = Field(min_length=3, max_length=2_000)
    mode: RagMode = RagMode.SELF_RAG
    top_k: int | None = Field(default=None, ge=1, le=12)


class ChatResponse(BaseModel):
    """Grounded answer, citations, and an educational execution trace."""

    answer: str
    mode: RagMode
    citations: list[Citation]
    trace: list[TraceStep]
    groundedness_score: float = Field(ge=0.0, le=1.0)


class IngestionResult(BaseModel):
    """Result of indexing one curated source."""

    source_id: str
    chunks_indexed: int
    object_key: str
    content_sha256: str


class EvalCase(BaseModel):
    """One deterministic evaluation example."""

    id: str
    question: str
    expected_terms: list[str] = Field(default_factory=list)
    expected_source_ids: list[str] = Field(default_factory=list)


class EvalCaseResult(BaseModel):
    """Metrics produced for one evaluation example."""

    case_id: str
    answer_relevance: float
    citation_recall: float
    citation_validity: float
    groundedness: float
    latency_ms: float
    passed: bool


class EvalRunResponse(BaseModel):
    """Aggregate evaluation report."""

    mode: RagMode
    cases: list[EvalCaseResult]
    averages: dict[str, float]
    pass_rate: float
