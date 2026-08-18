"""Behavior tests for the three retrieval strategies."""

from __future__ import annotations

from typing import Any

import pytest

from directors_rag.domain.models import ChatRequest, RagMode, RetrievedChunk
from directors_rag.rag.service import RagService


def retrieved(*, chunk_id: str = "one", score: float = 0.8) -> RetrievedChunk:
    """Build a retrieval result with enough evidence for grounding checks."""
    return RetrievedChunk(
        id=chunk_id,
        source_id="directing",
        source_title="Directing Handbook",
        source_url="https://example.com/directing",
        license="CC BY 4.0",
        text=(
            "Blocking arranges performers within a scene. Directors use blocking to express "
            "character relationships, power, distance, and emotional change."
        ),
        chunk_index=0,
        content_sha256="abc",
        score=score,
    )


class FakeEmbedder:
    """Return a stable query vector."""

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


class FakeVectors:
    """Return configured rankings in call order."""

    def __init__(self, rankings: list[list[RetrievedChunk]]) -> None:
        self.rankings = rankings
        self.calls = 0

    def search(self, vector: list[float], limit: int) -> list[RetrievedChunk]:
        del vector, limit
        ranking = self.rankings[min(self.calls, len(self.rankings) - 1)]
        self.calls += 1
        return ranking


class FakeLlm:
    """Return configured generations in call order."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = answers
        self.prompts: list[str] = []

    async def generate(self, system: str, prompt: str, **kwargs: Any) -> str:
        del system, kwargs
        self.prompts.append(prompt)
        return self.answers.pop(0)


def service(vectors: FakeVectors, llm: FakeLlm) -> RagService:
    """Construct the service with small in-memory fakes."""
    return RagService(  # type: ignore[arg-type]
        FakeEmbedder(),  # type: ignore[arg-type]
        vectors,
        llm,  # type: ignore[arg-type]
        relevance_threshold=0.35,
    )


@pytest.mark.asyncio
async def test_empty_index_returns_actionable_message_without_llm() -> None:
    llm = FakeLlm([])
    result = await service(FakeVectors([[]]), llm).ask(
        ChatRequest(question="What is blocking?", mode=RagMode.NAIVE)
    )
    assert result.groundedness_score == 0
    assert "Ingest" in result.answer
    assert not llm.prompts


@pytest.mark.asyncio
async def test_cited_mode_returns_provenance_and_grounding() -> None:
    llm = FakeLlm(["Blocking arranges performers to express character relationships [1]."])
    result = await service(FakeVectors([[retrieved()]]), llm).ask(
        ChatRequest(question="How does blocking express character?", mode=RagMode.CITED)
    )
    assert result.citations[0].source_id == "directing"
    assert result.groundedness_score > 0.7
    assert [step.stage for step in result.trace] == ["retrieve", "grounding_check"]


@pytest.mark.asyncio
async def test_self_rag_rewrites_a_weak_retrieval_query() -> None:
    vectors = FakeVectors([[retrieved(score=0.1)], [retrieved(chunk_id="two", score=0.9)]])
    llm = FakeLlm(
        [
            "blocking character relationship scene direction",
            "Blocking arranges performers to express character relationships [1].",
        ]
    )
    result = await service(vectors, llm).ask(
        ChatRequest(question="How should people move?", mode=RagMode.SELF_RAG)
    )
    assert vectors.calls == 2
    assert "query_rewrite" in [step.stage for step in result.trace]
    assert result.citations[0].score == 0.9


@pytest.mark.asyncio
async def test_self_rag_repairs_a_weak_draft() -> None:
    llm = FakeLlm(
        [
            "A profitable movie always uses blue lenses.",
            "Blocking arranges performers and communicates character relationships [1].",
        ]
    )
    result = await service(FakeVectors([[retrieved()]]), llm).ask(
        ChatRequest(question="What does blocking communicate?", mode=RagMode.SELF_RAG)
    )
    assert result.trace[-1].stage == "critique_and_retry"
    assert "[1]" in result.answer
