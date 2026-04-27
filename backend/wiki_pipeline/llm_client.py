"""OpenAI-compatible vLLM wrapper with per-task model routing."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    model: str


class LLMClient:
    """Thin wrapper around an OpenAI-compatible endpoint (vLLM).

    Routes ingest/lint/chat tasks to potentially different served models
    via VLLM_INGEST_MODEL / VLLM_LINT_MODEL / VLLM_CHAT_MODEL env vars.
    """

    def __init__(self) -> None:
        from openai import OpenAI

        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8080/v1")
        self.api_key = os.getenv("VLLM_API_KEY", "EMPTY")
        self.default_model = os.getenv("VLLM_DEFAULT_MODEL", "default")
        self.task_models = {
            "ingest": os.getenv("VLLM_INGEST_MODEL", self.default_model),
            "lint": os.getenv("VLLM_LINT_MODEL", self.default_model),
            "chat": os.getenv("VLLM_CHAT_MODEL", self.default_model),
        }
        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _model_for(self, task: str) -> str:
        return self.task_models.get(task, self.default_model)

    def complete(
        self,
        messages: list[dict],
        task: str = "ingest",
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Non-streaming chat completion."""
        model = self._model_for(task)
        params: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update(kwargs)

        resp = self._client.chat.completions.create(**params)
        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        return LLMResponse(content=content, tokens_used=int(tokens or 0), model=model)

    def stream(
        self,
        messages: list[dict],
        task: str = "chat",
        temperature: float = 0.7,
        **kwargs,
    ) -> Iterator[str]:
        """Streaming chat completion. Yields text chunks as they arrive."""
        model = self._model_for(task)
        params: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        params.update(kwargs)

        stream = self._client.chat.completions.create(**params)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                yield text


_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Lazy singleton — defers vLLM connection until first use."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm_client() -> None:
    """Clear the cached client (useful for tests / config reloads)."""
    global _client
    _client = None
