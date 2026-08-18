"""Deterministic RAG evaluation metrics suitable for CI smoke tests."""

from __future__ import annotations

from directors_rag.domain.models import Citation
from directors_rag.rag.grounding import content_terms


def expected_term_recall(answer: str, expected_terms: list[str]) -> float:
    """Measure the share of expected concepts represented in an answer."""
    if not expected_terms:
        return 1.0
    normalized = answer.lower()
    matched = sum(1 for term in expected_terms if term.lower() in normalized)
    return round(matched / len(expected_terms), 3)


def source_recall(citations: list[Citation], expected_source_ids: list[str]) -> float:
    """Measure whether expected evidence sources appeared in retrieval."""
    if not expected_source_ids:
        return 1.0
    actual = {citation.source_id for citation in citations}
    return round(len(actual & set(expected_source_ids)) / len(set(expected_source_ids)), 3)


def citations_are_valid(answer: str, citations: list[Citation]) -> float:
    """Measure whether the response citations are present in the returned source set."""
    expected = {f"[{citation.number}]" for citation in citations}
    used = {token for token in answer.split() if token.startswith("[") and token.endswith("]")}
    if not used:
        return 0.0
    return round(len(used & expected) / len(used), 3)


def question_overlap(question: str, answer: str) -> float:
    """Provide a small transparent topicality signal for diagnostics."""
    question_terms = content_terms(question)
    if not question_terms:
        return 1.0
    answer_terms = content_terms(answer)
    return round(len(question_terms & answer_terms) / len(question_terms), 3)
