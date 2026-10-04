"""LLM provider for any OpenAI-compatible chat-completions endpoint.

Huawei Cloud ModelArts MaaS exposes hosted models through this API shape, so the
same class works there or with any other compatible host. The model is only
asked to extract/classify/normalise; it never computes business metrics.
"""

import httpx

from app.core.config import get_settings
from app.providers.base import LLM_UNAVAILABLE_MSG, ProviderUnavailable


class OpenAICompatibleLLMProvider:
    name = "openai-compatible"

    def __init__(self, client: httpx.Client | None = None) -> None:
        s = get_settings()
        self.base_url = s.llm_base_url.rstrip("/")
        self.api_key = s.llm_api_key
        self.model = s.llm_model
        self.client = client or httpx.Client(timeout=s.llm_timeout_seconds)
        self.name = f"llm:{self.model}" if self.model else "llm"

    def complete_json(self, system: str, user: str) -> str:
        if not (self.base_url and self.model):
            raise ProviderUnavailable(LLM_UNAVAILABLE_MSG, "LLM_BASE_URL / LLM_MODEL not configured")
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        try:
            resp = self.client.post(f"{self.base_url}/chat/completions", json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(LLM_UNAVAILABLE_MSG, f"LLM request failed: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise ProviderUnavailable(LLM_UNAVAILABLE_MSG, f"LLM returned HTTP {resp.status_code}")
        try:
            return resp.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderUnavailable(LLM_UNAVAILABLE_MSG, "LLM response had an unexpected shape") from exc
