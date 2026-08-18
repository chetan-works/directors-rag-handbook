"""Small asynchronous client for the local Ollama chat API."""

from __future__ import annotations

import httpx


class OllamaChatClient:
    """Generate text with an open-source model served by Ollama."""

    def __init__(self, base_url: str, model: str, timeout_seconds: float = 90.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        """Return a single non-streaming assistant message."""
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/api/chat", json=payload)
            response.raise_for_status()
        content = response.json().get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("The local language model returned an empty response")
        return content.strip()

    async def is_ready(self) -> bool:
        """Return whether Ollama is reachable and the selected model is installed."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
            models = response.json().get("models", [])
            names = {item.get("name", "").split(":")[0] for item in models}
            return self._model.split(":")[0] in names
        except (httpx.HTTPError, ValueError):
            return False
