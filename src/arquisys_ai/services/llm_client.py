from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        ...


class NullLLMClient:
    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        return ""


class OpenAILLMClient:
    def __init__(self, model: str, api_key: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for OpenAILLMClient") from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        response = self._client.responses.create(
            model=self._model,
            temperature=temperature,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
        )

        output_text = getattr(response, "output_text", "")
        return output_text.strip() if output_text else ""
