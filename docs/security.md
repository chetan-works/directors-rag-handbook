# Security

## Current threat model

Project 1 is a single-operator educational demo over publicly licensed sources. It does not claim to
provide user accounts, tenant isolation, financial-document handling, or public-internet production
hardening. Those requirements belong to Project 2 and require a different authorization model.

## Implemented controls

- Shared `X-API-Key` authentication with constant-time comparison.
- Pydantic request limits and an application-level requests-per-minute guard.
- Exact catalog URL resolution; clients cannot supply ingestion URLs.
- HTTPS-only fetches, same-host redirect policy, response-size caps, and format-specific parsing.
- Source data delimited as untrusted context in the system prompt.
- CORS allowlist, trusted-host checks, restrictive security headers, and disabled production docs.
- Generic client errors with server-side incident IDs.
- MinIO, Qdrant, and Ollama on an internal Compose network.
- Non-root application container and environment-injected credentials.

## Before internet exposure

1. Terminate TLS at a maintained reverse proxy or managed load balancer.
2. Replace the shared key with OIDC/OAuth2 and short-lived access tokens.
3. Put administrative ingestion/evaluation endpoints behind a separate role.
4. Keep ports 9000, 9001, 6333, and 11434 private; remove their host mappings in production.
5. Use a secret manager, rotate all initial credentials, and enable MinIO server-side encryption.
6. Replace in-memory rate limiting with a gateway or distributed store.
7. Pin images by digest, scan them, generate an SBOM, sign releases, and enable dependency updates.
8. Add centralized audit logs without prompts, retrieved passages, API keys, or personal data.
9. Apply egress controls so the ingestion worker can reach only reviewed publisher hosts.
10. Run a focused security review before adding private documents or multiple users.

## Prompt injection

Retrieved text is untrusted. The prompt explicitly rejects instructions inside it and wraps every
chunk in source boundaries. This reduces risk but cannot eliminate prompt injection. High-impact
actions must never be granted to the language model; this app gives it no tools and validates all
source selection outside the model.
