"""Transparent, deterministic grounding checks used by Self-RAG and evaluations."""

from __future__ import annotations

import re

from directors_rag.domain.models import RetrievedChunk

_WORD = re.compile(r"[a-zA-Z][a-zA-Z'-]{2,}")
_CITATION = re.compile(r"\[(\d+)]")
_STOPWORDS = {
    "and",
    "are",
    "but",
    "for",
    "from",
    "have",
    "into",
    "not",
    "that",
    "the",
    "their",
    "this",
    "was",
    "were",
    "with",
    "you",
    "your",
}


def content_terms(text: str) -> set[str]:
    """Return normalized non-stopword terms for lightweight lexical metrics."""
    return {match.group(0).lower() for match in _WORD.finditer(text)} - _STOPWORDS


def citation_validity(answer: str, source_count: int) -> float:
    """Measure whether citation markers refer only to supplied context blocks."""
    markers = [int(item) for item in _CITATION.findall(answer)]
    if not markers:
        return 0.0
    valid = sum(1 for marker in markers if 1 <= marker <= source_count)
    return valid / len(markers)


def lexical_groundedness(answer: str, chunks: list[RetrievedChunk]) -> float:
    """Estimate support as the share of answer terms present in retrieved evidence."""
    answer_terms = content_terms(_CITATION.sub("", answer))
    if not answer_terms:
        return 0.0
    context_terms = content_terms(" ".join(chunk.text for chunk in chunks))
    return min(1.0, len(answer_terms & context_terms) / len(answer_terms))


def combined_groundedness(answer: str, chunks: list[RetrievedChunk], *, citations: bool) -> float:
    """Combine lexical evidence overlap with citation validity."""
    lexical = lexical_groundedness(answer, chunks)
    if not citations:
        return round(lexical, 3)
    validity = citation_validity(answer, len(chunks))
    return round((0.7 * lexical) + (0.3 * validity), 3)
