"""Run a version-controlled golden dataset through the live RAG service."""

from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import TypeAdapter

from directors_rag.domain.models import (
    ChatRequest,
    EvalCase,
    EvalCaseResult,
    EvalRunResponse,
    RagMode,
)
from directors_rag.evaluation.metrics import (
    citations_are_valid,
    expected_term_recall,
    question_overlap,
    source_recall,
)
from directors_rag.rag.service import RagService


class EvaluationHarness:
    """Execute end-to-end examples and aggregate explainable metrics."""

    def __init__(self, rag_service: RagService, dataset_path: Path) -> None:
        self._rag = rag_service
        self._dataset_path = dataset_path

    def load_cases(self) -> list[EvalCase]:
        """Load newline-delimited JSON cases with strict validation."""
        with self._dataset_path.open(encoding="utf-8") as handle:
            records = [json.loads(line) for line in handle if line.strip()]
        return TypeAdapter(list[EvalCase]).validate_python(records)

    async def run(self, mode: RagMode) -> EvalRunResponse:
        """Run every case sequentially to avoid overloading a local model."""
        results: list[EvalCaseResult] = []
        for case in self.load_cases():
            started = time.perf_counter()
            response = await self._rag.ask(ChatRequest(question=case.question, mode=mode))
            latency_ms = (time.perf_counter() - started) * 1_000
            term_score = expected_term_recall(response.answer, case.expected_terms)
            citation_recall = source_recall(response.citations, case.expected_source_ids)
            validity = citations_are_valid(response.answer, response.citations)
            topicality = question_overlap(case.question, response.answer)
            relevance = round((0.75 * term_score) + (0.25 * topicality), 3)
            passed = (
                relevance >= 0.5 and citation_recall >= 0.5 and response.groundedness_score >= 0.5
            )
            results.append(
                EvalCaseResult(
                    case_id=case.id,
                    answer_relevance=relevance,
                    citation_recall=citation_recall,
                    citation_validity=validity,
                    groundedness=response.groundedness_score,
                    latency_ms=round(latency_ms, 2),
                    passed=passed,
                )
            )
        metric_names = (
            "answer_relevance",
            "citation_recall",
            "citation_validity",
            "groundedness",
            "latency_ms",
        )
        count = len(results)
        averages = {
            name: round(sum(getattr(result, name) for result in results) / count, 3)
            if count
            else 0.0
            for name in metric_names
        }
        pass_rate = round(sum(result.passed for result in results) / count, 3) if count else 0.0
        return EvalRunResponse(mode=mode, cases=results, averages=averages, pass_rate=pass_rate)
