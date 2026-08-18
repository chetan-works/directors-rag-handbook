# Deployment and public endpoints

GitHub stores, reviews, tests, documents, and releases the project. GitHub Pages publishes the
static documentation, but it cannot execute this Python and database stack. The live API and UI need
a container host.

## Recommended first production shape

Use one Linux VPS with Docker Compose, persistent volumes, at least 4 CPU cores and 12 GB RAM. Point
two DNS `A` records at the server:

- `api.your-domain.example` for FastAPI.
- `rag.your-domain.example` for Streamlit.

The production Compose override adds Caddy. Caddy is the only public-facing service and provisions
HTTPS certificates automatically. MinIO, Qdrant, and Ollama remain bound to the server's loopback
interface and the private Compose network.

## Server commands

```bash
git clone https://github.com/chetan-works/directors-rag-handbook.git
cd directors-rag-handbook
cp .env.production.example .env
# Edit domains, ACME email, and every placeholder secret in .env.
docker compose -f compose.yaml -f compose.production.yaml up -d minio qdrant ollama
docker compose -f compose.yaml -f compose.production.yaml --profile setup run --rm ollama-pull
docker compose -f compose.yaml -f compose.production.yaml up -d --build api ui caddy
docker compose -f compose.yaml -f compose.production.yaml ps
```

Verify from a different machine:

```bash
curl https://api.your-domain.example/health/live
curl -H "X-API-Key: YOUR_KEY" https://api.your-domain.example/api/v1/sources
```

Your main endpoint is `POST https://api.your-domain.example/api/v1/chat`. In production, interactive
API docs are disabled intentionally; export the OpenAPI schema during CI if public reference docs are
needed.

## Updating the deployment

```bash
git pull --ff-only
docker compose -f compose.yaml -f compose.production.yaml build api ui
docker compose -f compose.yaml -f compose.production.yaml up -d --no-deps api ui
```

For the first release, keep deployment manual and observable. After the server is stable, add a
protected GitHub environment and a narrowly scoped deployment mechanism. Do not place SSH private
keys, `.env`, model data, or API keys in the repository.

## Endpoint security checklist

- Allow inbound TCP 80/443 and UDP 443 only; restrict SSH to an administrator IP.
- Confirm ports 8000, 8501, 9000, 9001, 6333, and 11434 are not publicly reachable.
- Use random 32+ character application and MinIO secrets.
- Back up the named MinIO and Qdrant volumes before upgrades.
- Add OIDC and role-separated administration before supporting multiple users.
- Monitor disk, RAM, request latency, Caddy logs, and container health.
