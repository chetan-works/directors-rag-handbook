"""Orchestrate plain, cited, and Self-RAG-style answer generation."""

from __future__ import annotations

import asyncio

from directors_rag.domain.models import (
    ChatRequest,
    ChatResponse,
    Citation,
    RagMode,
    RetrievedChunk,
    TraceStep,
)
from directors_rag.rag.grounding import combined_groundedness
from directors_rag.rag.llm import OllamaChatClient
from directors_rag.rag.prompts import SYSTEM_PROMPT, answer_prompt, repair_prompt, rewrite_prompt
from directors_rag.retrieval.embeddings import FastEmbedder
from directors_rag.retrieval.vector_store import QdrantVectorStore


class RagService:
    """Execute an inspectable RAG strategy for a user question."""

    def __init__(
        self,
        embedder: FastEmbedder,
        vector_store: QdrantVectorStore,
        llm: OllamaChatClient,
        *,
        default_top_k: int = 6,
        relevance_threshold: float = 0.35,
    ) -> None:
        self._embedder = embedder
        self._vectors = vector_store
        self._llm = llm
        self._default_top_k = default_top_k
        self._threshold = relevance_threshold

    async def ask(self, request: ChatRequest) -> ChatResponse:
        """Retrieve evidence, generate an answer, and optionally self-correct it."""
        top_k = request.top_k or self._default_top_k
        trace: list[TraceStep] = []
        chunks = await self._retrieve(request.question, top_k)
        trace.append(self._retrieval_trace("retrieve", request.question, chunks))

        if not chunks:
            return ChatResponse(
                answer=(
                    "The handbook has no indexed evidence yet. Ingest the curated sources first."
                ),
                mode=request.mode,
                citations=[],
                trace=trace,
                groundedness_score=0.0,
            )

        if request.mode is RagMode.SELF_RAG and chunks[0].score < self._threshold:
            rewritten = await self._llm.generate(
                SYSTEM_PROMPT,
                rewrite_prompt(request.question),
                temperature=0.0,
            )
            second_pass = await self._retrieve(rewritten, top_k)
            chunks = self._merge_rankings(chunks, second_pass, top_k)
            trace.append(self._retrieval_trace("query_rewrite", rewritten, chunks))

        answer = await self._llm.generate(
            SYSTEM_PROMPT,
            answer_prompt(request.question, chunks, request.mode),
        )
        expects_citations = request.mode is not RagMode.NAIVE
        score = combined_groundedness(answer, chunks, citations=expects_citations)
        trace.append(
            TraceStep(
                stage="grounding_check",
                detail="Deterministic lexical support and citation-validity check.",
                values={"score": score, "threshold": 0.55},
            )
        )

        if request.mode is RagMode.SELF_RAG and score < 0.55:
            answer = await self._llm.generate(
                SYSTEM_PROMPT,
                repair_prompt(
                    request.question,
                    answer,
                    chunks,
                    "weak evidence overlap or citations",
                ),
                temperature=0.0,
            )
            score = combined_groundedness(answer, chunks, citations=True)
            trace.append(
                TraceStep(
                    stage="critique_and_retry",
                    detail="The draft was regenerated with stricter evidence constraints.",
                    values={"revised_score": score},
                )
            )

        return ChatResponse(
            answer=answer,
            mode=request.mode,
            citations=self._citations(chunks),
            trace=trace,
            groundedness_score=score,
        )

    async def _retrieve(self, query: str, top_k: int) -> list[RetrievedChunk]:
        vector = await asyncio.to_thread(self._embedder.embed_query, query)
        return await asyncio.to_thread(self._vectors.search, vector, top_k)

    @staticmethod
    def _merge_rankings(
        first: list[RetrievedChunk],
        second: list[RetrievedChunk],
        limit: int,
    ) -> list[RetrievedChunk]:
        by_id = {chunk.id: chunk for chunk in first}
        for chunk in second:
            existing = by_id.get(chunk.id)
            if existing is None or chunk.score > existing.score:
                by_id[chunk.id] = chunk
        return sorted(by_id.values(), key=lambda chunk: chunk.score, reverse=True)[:limit]

    @staticmethod
    def _citations(chunks: list[RetrievedChunk]) -> list[Citation]:
        return [
            Citation(
                number=number,
                source_id=chunk.source_id,
                title=chunk.source_title,
                url=chunk.source_url,
                excerpt=(chunk.text[:277].rsplit(" ", 1)[0] + "…")
                if len(chunk.text) > 280
                else chunk.text,
                page=chunk.page,
                score=round(chunk.score, 4),
            )
            for number, chunk in enumerate(chunks, start=1)
        ]

    @staticmethod
    def _retrieval_trace(stage: str, query: str, chunks: list[RetrievedChunk]) -> TraceStep:
        return TraceStep(
            stage=stage,
            detail=f"Retrieved {len(chunks)} chunks from Qdrant.",
            values={
                "query": query,
                "top_score": round(chunks[0].score, 4) if chunks else None,
                "source_ids": list(dict.fromkeys(chunk.source_id for chunk in chunks)),
            },
        )
