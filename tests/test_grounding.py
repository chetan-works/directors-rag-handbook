"""Tests for deterministic grounding metrics."""

from directors_rag.domain.models import RetrievedChunk
from directors_rag.rag.grounding import citation_validity, combined_groundedness


def chunk() -> RetrievedChunk:
    """Return a representative retrieval result."""
    return RetrievedChunk(
        id="188b063c-b7f2-4db5-8c50-3d037b31fddd",
        source_id="source-one",
        source_title="Directing",
        source_url="https://example.com",
        license="CC BY 4.0",
        text="Blocking arranges performers in the scene to express character relationships.",
        chunk_index=0,
        content_sha256="abc",
        score=0.8,
    )


def test_citation_validity_rejects_unknown_numbers() -> None:
    assert citation_validity("Blocking matters [1], but not [9].", 1) == 0.5


def test_grounded_answer_scores_above_unsupported_answer() -> None:
    supported = combined_groundedness(
        "Blocking arranges performers and expresses character relationships [1].",
        [chunk()],
        citations=True,
    )
    unsupported = combined_groundedness(
        "A telephoto lens always guarantees a profitable production [1].",
        [chunk()],
        citations=True,
    )
    assert supported > unsupported
