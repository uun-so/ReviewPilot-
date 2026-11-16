"""LLM provider interface and the DeepSeek Responses API adapter."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)


class LLMError(RuntimeError):
    """Provider-level failure (network, auth, empty or malformed output)."""


class LLMResponseError(LLMError):
    """The provider returned something that is not valid JSON."""


class LLMProvider(Protocol):
    def complete_json(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        schema: dict[str, Any],
        schema_name: str,
        effort: str = "none",
        max_output_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Return parsed JSON plus token usage."""
        ...


def _output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return text
    parts: list[str] = []
    for item in getattr(response, "output", None) or []:
        for content in getattr(item, "content", None) or []:
            value = getattr(content, "text", None)
            if value:
                parts.append(value)
    return "".join(parts)


def _strip_code_fence(text: str) -> str:
    """Normalize a JSON payload that may be wrapped in a Markdown fence."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    result = {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }
    details = getattr(usage, "output_tokens_details", None)
    reasoning = int(getattr(details, "reasoning_tokens", 0) or 0) if details else 0
    if reasoning:
        result["reasoning_tokens"] = reasoning
    return result


class DeepSeekProvider:
    """DeepSeek Responses API via the OpenAI-compatible Python SDK.

    ``text.format=json_schema`` is used so the API enforces the shape; the
    caller still validates with Pydantic and retries once on failure.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key and client is None:
            raise LLMError("DEEPSEEK_API_KEY 未设置；请在 .env 或环境变量中提供。")
        self._client = client or OpenAI(
            api_key=key,
            base_url=base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )

    def complete_json(
        self,
        *,
        model: str,
        instructions: str,
        input: str,
        schema: dict[str, Any],
        schema_name: str,
        effort: str = "none",
        max_output_tokens: int = 2048,
        temperature: float = 0.0,
    ) -> tuple[dict[str, Any], dict[str, int]]:
        request: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": input,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                }
            },
            "reasoning": {"effort": effort},
            "max_output_tokens": max_output_tokens,
        }
        if effort == "none":
            request["temperature"] = temperature

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.responses.create(**request)
                text = _output_text(response)
                if not text.strip():
                    raise LLMResponseError(
                        f"{schema_name}: 模型返回了空内容"
                    )
                normalized = _strip_code_fence(text)
                try:
                    data = json.loads(normalized)
                except json.JSONDecodeError as exc:
                    preview = text[:200].replace("\n", "\\n")
                    raise LLMResponseError(
                        f"{schema_name}: 模型输出不是合法 JSON（{preview!r}）：{exc}"
                    ) from exc
                if not isinstance(data, dict):
                    raise LLMResponseError(f"{schema_name}: JSON 顶层不是对象")
                return data, _usage(response)
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                if attempt == 2:
                    break
                time.sleep(2**attempt)
            except APIStatusError as exc:
                last_error = exc
                if exc.status_code >= 500 and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise LLMError(f"DeepSeek API 错误（HTTP {exc.status_code}）：{exc}") from exc
            except LLMResponseError as exc:
                # Empty or malformed structured output is retryable per the
                # provider docs (blank content can appear even with stop).
                last_error = exc
                if attempt == 2:
                    break
                time.sleep(1 + attempt)
        if isinstance(last_error, LLMError):
            raise last_error
        raise LLMError(f"DeepSeek API 调用失败：{last_error}") from last_error
