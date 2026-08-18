"""Tests for evaluation metrics and harness aggregation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from directors_rag.domain.models import ChatResponse, Citation, RagMode
from directors_rag.evaluation.harness import EvaluationHarness
from directors_rag.evaluation.metrics import (
    citations_are_valid,
    expected_term_recall,
    question_overlap,
    source_recall,
)


def citation() -> Citation:
    """Return a stable citation."""
    return Citation(
        number=1,
        source_id="directing",
        title="Directing",
        url="https://example.com",
        excerpt="Blocking expresses relationships.",
        score=0.9,
    )


def test_metrics_cover_empty_and_matching_expectations() -> None:
    assert expected_term_recall("Blocking shapes a scene", []) == 1
    assert expected_term_recall("Blocking shapes a scene", ["blocking", "lens"]) == 0.5
    assert source_recall([citation()], []) == 1
    assert source_recall([citation()], ["directing", "editing"]) == 0.5
    assert citations_are_valid("An uncited answer", [citation()]) == 0
    assert citations_are_valid("An answer [1]", [citation()]) == 1
    assert question_overlap("What is blocking?", "Blocking arranges actors") > 0


class FakeRag:
    """Return a deterministic answer for each evaluation case."""

    async def ask(self, request: object) -> ChatResponse:
        del request
        return ChatResponse(
            answer="Blocking expresses character relationships in the scene [1]",
            mode=RagMode.CITED,
            citations=[citation()],
            trace=[],
            groundedness_score=0.8,
        )


@pytest.mark.asyncio
async def test_harness_loads_jsonl_and_aggregates(tmp_path: Path) -> None:
    dataset = tmp_path / "golden.jsonl"
    record = {
        "id": "blocking",
        "question": "How does blocking express relationships?",
        "expected_terms": ["blocking", "relationships"],
        "expected_source_ids": ["directing"],
    }
    dataset.write_text(json.dumps(record) + "\n", encoding="utf-8")
    harness = EvaluationHarness(FakeRag(), dataset)  # type: ignore[arg-type]

    assert harness.load_cases()[0].id == "blocking"
    report = await harness.run(RagMode.CITED)
    assert report.pass_rate == 1
    assert report.averages["citation_recall"] == 1
