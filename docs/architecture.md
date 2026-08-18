# Architecture

## Request path

```mermaid
sequenceDiagram
    actor User
    participant UI as Streamlit
    participant API as FastAPI
    participant E as FastEmbed
    participant Q as Qdrant
    participant L as Ollama

    User->>UI: Ask a filmmaking question
    UI->>API: POST /api/v1/chat + X-API-Key
    API->>E: Embed question
    E-->>API: Query vector
    API->>Q: Similarity search
    Q-->>API: Chunks + provenance + scores
    opt Self-RAG and weak retrieval
        API->>L: Rewrite search query
        API->>E: Embed rewritten query
        API->>Q: Second search
    end
    API->>L: Generate from delimited evidence
    L-->>API: Draft answer
    API->>API: Grounding and citation check
    opt Self-RAG and weak draft
        API->>L: Critique-and-revise prompt
    end
    API-->>UI: Answer + citations + trace + score
```

## Ingestion path

The catalog is code-reviewed YAML. An administrator selects a source ID; the service resolves its
exact HTTPS URL, blocks cross-host redirects, limits response size, archives the raw bytes, extracts
semantic sections, creates deterministic overlapping chunks, embeds them locally, and upserts them
into Qdrant. Each chunk includes its source URL, license, page/heading, content hash, and stable ID.

## Module boundaries

- `domain` has no infrastructure dependencies beyond Pydantic.
- `ingestion` turns reviewed external material into domain chunks.
- `retrieval` isolates embedding and vector-database SDKs.
- `storage` isolates S3-compatible object persistence.
- `rag` owns prompts, model calls, grounding checks, and strategy orchestration.
- `evaluation` owns datasets and metrics, not production answer logic.
- `api` performs transport, authentication, configuration, and dependency wiring.
- `ui` is a thin API client and never talks directly to data stores.

This separation is intentional: Project 2 can introduce tenant-aware adapters without mixing private
document policy into the public handbook application.
