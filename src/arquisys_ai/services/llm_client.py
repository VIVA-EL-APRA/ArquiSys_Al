from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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


class OllamaClient:
    def __init__(self, model: str, base_url: str | None = None):
        self._model = model
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._endpoint = f"{self._base_url}/api/generate"

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        payload = {
            "model": self._model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "temperature": temperature,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
            result = json.loads(body)
            return str(result.get("response", "")).strip()
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
