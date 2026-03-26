from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from typing import Any
from urllib import error, request

from pydantic import BaseModel

from app.core.config import settings


class LLMProviderError(RuntimeError):
    """Raised when a configured provider fails to return valid structured output."""


class LLMProviderNotConfiguredError(LLMProviderError):
    """Raised when no provider can be constructed from the current settings."""


@dataclass(frozen=True, slots=True)
class LLMStructuredResult:
    provider_name: str
    model: str
    payload: dict[str, Any]
    raw_response: dict[str, Any]


class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    def generate_structured_output(
        self,
        *,
        schema_name: str,
        schema_model: type[BaseModel],
        instructions: str,
        input_text: str,
    ) -> LLMStructuredResult:
        raise NotImplementedError


class OpenAIResponsesProvider(LLMProvider):
    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str,
        timeout_seconds: int,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._reasoning_effort = reasoning_effort
        self._timeout_seconds = timeout_seconds

    def generate_structured_output(
        self,
        *,
        schema_name: str,
        schema_model: type[BaseModel],
        instructions: str,
        input_text: str,
    ) -> LLMStructuredResult:
        body = {
            "model": self._model,
            "instructions": instructions,
            "input": input_text,
            "reasoning": {"effort": self._reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema_model.model_json_schema(),
                }
            },
        }
        response_json = self._make_request(body)
        payload = self._extract_payload(response_json)
        return LLMStructuredResult(
            provider_name=self.provider_name,
            model=self._model,
            payload=payload,
            raw_response=response_json,
        )

    def _make_request(self, body: dict[str, Any]) -> dict[str, Any]:
        raw_request = json.dumps(body).encode("utf-8")
        req = request.Request(
            "https://api.openai.com/v1/responses",
            data=raw_request,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMProviderError(
                f"OpenAI Responses API request failed with status {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise LLMProviderError(f"OpenAI Responses API request failed: {exc.reason}") from exc

    def _extract_payload(self, response_json: dict[str, Any]) -> dict[str, Any]:
        output_items = response_json.get("output")
        if not isinstance(output_items, list):
            raise LLMProviderError("OpenAI response did not include output items.")

        for item in output_items:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                if not isinstance(content, dict) or content.get("type") != "output_text":
                    continue
                text = content.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise LLMProviderError("Structured output text was not valid JSON.") from exc
                if not isinstance(payload, dict):
                    raise LLMProviderError("Structured output must be a JSON object.")
                return payload

        raise LLMProviderError("OpenAI response did not include structured output text.")


def get_llm_provider() -> LLMProvider:
    provider_name = settings.helper_llm_provider.strip().lower()
    if not provider_name or provider_name == "none":
        raise LLMProviderNotConfiguredError("No helper LLM provider is configured.")

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise LLMProviderNotConfiguredError(
                "OPENAI_API_KEY is required when HELPER_LLM_PROVIDER is set to 'openai'."
            )
        return OpenAIResponsesProvider(
            api_key=settings.openai_api_key,
            model=settings.helper_llm_model,
            reasoning_effort=settings.helper_llm_reasoning_effort,
            timeout_seconds=settings.helper_llm_timeout_seconds,
        )

    raise LLMProviderNotConfiguredError(
        f"Unsupported helper LLM provider '{settings.helper_llm_provider}'."
    )
