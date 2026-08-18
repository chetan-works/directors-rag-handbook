"""Streamlit interface for chat, source ingestion, and RAG evaluations."""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

st.set_page_config(
    page_title="Director's RAG Handbook",
    page_icon="🎬",
    layout="wide",
)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("APP_API_KEY", "")
HEADERS = {"X-API-Key": API_KEY}


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    """Call the backend and surface safe, useful errors in the UI."""
    try:
        response = httpx.request(
            method,
            f"{BACKEND_URL}{path}",
            headers=HEADERS,
            timeout=300,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get("detail", error.response.text)
        except ValueError:
            detail = error.response.text
        st.error(f"Backend returned {error.response.status_code}: {detail}")
    except httpx.HTTPError as error:
        st.error(f"Cannot reach the API at {BACKEND_URL}: {error}")
    return None


def render_chat() -> None:
    """Render the side-by-side educational chat experience."""
    st.subheader("Ask the director's handbook")
    st.caption("Every answer exposes the retrieval path, evidence, and grounding score.")
    mode_labels = {
        "Self-RAG": "self_rag",
        "Citation-first RAG": "cited",
        "Naive RAG": "naive",
    }
    left, right = st.columns([2, 1])
    with left:
        mode_label = st.selectbox("Strategy", list(mode_labels), index=0)
        question = st.text_area(
            "Question",
            placeholder="How should a director use blocking to reveal character relationships?",
            height=110,
        )
        ask = st.button("Search the handbook", type="primary", use_container_width=True)
    with right:
        st.info(
            "**Self-RAG** retries weak retrieval and critiques poorly grounded drafts. "
            "**Citation-first** retrieves once and requires citations. **Naive** is the baseline."
        )

    if ask and question.strip():
        with st.spinner("Retrieving, reasoning, and checking evidence…"):
            result = api_request(
                "POST",
                "/api/v1/chat",
                json={"question": question, "mode": mode_labels[mode_label]},
            )
        if not result:
            return
        score = float(result["groundedness_score"])
        st.metric("Grounding score", f"{score:.0%}")
        st.markdown(result["answer"])
        citations, trace = st.tabs(["Evidence", "Execution trace"])
        with citations:
            for citation in result["citations"]:
                location = f" · page {citation['page']}" if citation.get("page") else ""
                with st.expander(
                    f"[{citation['number']}] {citation['title']}{location} "
                    f"· similarity {citation['score']:.3f}"
                ):
                    st.write(citation["excerpt"])
                    st.link_button("Open original source", citation["url"])
        with trace:
            for step in result["trace"]:
                st.markdown(f"**{step['stage'].replace('_', ' ').title()}** — {step['detail']}")
                st.json(step["values"], expanded=False)


def render_library() -> None:
    """Render source provenance and explicit ingestion controls."""
    st.subheader("Curated open-source library")
    st.caption("Only exact URLs reviewed in `data/sources.yaml` can be fetched.")
    sources = api_request("GET", "/api/v1/sources")
    if not sources:
        return
    for source in sources:
        with st.container(border=True):
            title, action = st.columns([4, 1])
            with title:
                st.markdown(f"#### {source['title']}")
                st.caption(f"{source['author']} · {source['license']}")
                st.write(" · ".join(source.get("tags", [])))
                st.link_button("Review source", source["attribution_url"])
            with action:
                if st.button(
                    "Ingest",
                    key=f"ingest-{source['id']}",
                    disabled=not source["enabled"],
                ):
                    with st.spinner("Archiving, chunking, embedding, and indexing…"):
                        result = api_request("POST", f"/api/v1/sources/{source['id']}/ingest")
                    if result:
                        st.success(f"Indexed {result['chunks_indexed']} chunks")


def render_evaluation() -> None:
    """Render the golden-dataset evaluation harness."""
    st.subheader("Evaluation harness")
    st.caption(
        "Run the same checked-in questions across strategies before changing prompts or models."
    )
    mode = st.selectbox("Evaluation strategy", ["self_rag", "cited", "naive"])
    if st.button("Run evaluation", type="primary"):
        with st.spinner("Running the golden dataset; local models may take several minutes…"):
            report = api_request("POST", f"/api/v1/evaluations/run?mode={mode}")
        if not report:
            return
        columns = st.columns(4)
        columns[0].metric("Pass rate", f"{report['pass_rate']:.0%}")
        columns[1].metric("Answer relevance", f"{report['averages']['answer_relevance']:.0%}")
        columns[2].metric("Citation recall", f"{report['averages']['citation_recall']:.0%}")
        columns[3].metric("Groundedness", f"{report['averages']['groundedness']:.0%}")
        st.dataframe(report["cases"], use_container_width=True, hide_index=True)


st.title("🎬 Director's RAG Handbook")
st.write("An inspectable lab for learning how retrieval-augmented generation behaves.")
chat_tab, library_tab, evaluation_tab = st.tabs(["Chat", "Source library", "Evaluations"])
with chat_tab:
    render_chat()
with library_tab:
    render_library()
with evaluation_tab:
    render_evaluation()
