from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arquisys_ai.services.llm_client import LLMClient


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    use_llm_for_analyst: bool
    ollama_model: str | None = None
    ollama_base_url: str | None = None
    use_ollama_for_analyst: bool = False
    _llm_client: "LLMClient | None" = field(default=None, repr=False)

    @property
    def analyst_llm_client(self) -> "LLMClient | None":
        if self._llm_client is not None:
            return self._llm_client

        if self.use_ollama_for_analyst and self.ollama_model:
            from arquisys_ai.services.llm_client import OllamaClient
            return OllamaClient(model=self.ollama_model, base_url=self.ollama_base_url)

        if self.use_llm_for_analyst and self.openai_api_key:
            from arquisys_ai.services.llm_client import OpenAILLMClient
            return OpenAILLMClient(model=self.openai_model, api_key=self.openai_api_key)

        return None


def get_settings() -> Settings:
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        use_llm_for_analyst=_as_bool(os.getenv("USE_LLM_FOR_ANALYST"), default=False),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:14b"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        use_ollama_for_analyst=_as_bool(os.getenv("USE_OLLAMA_FOR_ANALYST"), default=False),
    )
