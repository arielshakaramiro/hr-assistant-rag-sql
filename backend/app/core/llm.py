"""Minimal OpenAI-compatible chat client over httpx.

One client serves both local Ollama (qwen2.5, $0, nothing leaves) and hosted Groq
(Llama 3.3 70B, free tier) — both speak the OpenAI /chat/completions shape. Provider is
chosen entirely by env (LLM_BASE_URL / LLM_API_KEY / LLM_MODEL), so swapping is config-only.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


class LLMError(RuntimeError):
    """Raised when the provider is unreachable or returns an error (mapped to LLM_UNAVAILABLE)."""


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 512,
    timeout: float = 60.0,
) -> str:
    """Return the assistant message content for a chat completion."""
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model or settings.llm_model,
        "messages": messages,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except httpx.HTTPError as exc:  # network error, 4xx/5xx, timeout
        raise LLMError(str(exc)) from exc
    data = resp.json()
    try:
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError) as exc:
        raise LLMError(f"unexpected response shape: {data}") from exc
