# Director's RAG Handbook

Learn RAG by watching it work. This open-source lab answers filmmaking questions with visible
evidence, citations, grounding checks, and execution traces.

## Three strategies, one knowledge base

| Strategy | What it demonstrates |
|---|---|
| Naive RAG | A simple retrieve-then-generate baseline |
| Citation-first RAG | A grounded prompt and inspectable sources |
| Self-RAG-inspired | Weak-retrieval query rewriting and weak-draft revision |

The live application is a Docker stack containing Streamlit, FastAPI, MinIO, Qdrant, FastEmbed, and
Ollama. GitHub Pages hosts this documentation showcase; a separate container host runs the app.

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up -d minio qdrant ollama
docker compose --profile setup run --rm ollama-pull
docker compose up -d --build api ui
```

Then visit `http://localhost:8501`, inspect the source catalog, ingest reviewed sources, and compare
the same question across all three modes.

## Design promises

- Every retrieval chunk carries a title, URL, license, content hash, and location where available.
- No arbitrary URL scraping endpoint exists.
- Raw indexed inputs remain reproducible in MinIO.
- Quality metrics are simple enough to inspect and challenge.
- Local models keep prompts and retrieved text on the operator's machine.
