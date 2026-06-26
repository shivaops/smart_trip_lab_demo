"""
core/llm_client.py
------------------
Provider-aware LLM adapter for Smart Trip.

Purpose in Phase 4A:
- Prepare ONE central place for calling the selected LLM provider.
- Keep provider-specific details out of graph/nodes later.
- Do NOT change chat flow by itself until later phases wire this file in.

Supported providers in this foundation file:
- GEMINI  -> Google Gemini REST call
- OLLAMA  -> Local Ollama HTTP call

Important:
- This file is intentionally standalone and safe to add first.
- Later phases will make nodes.py call these functions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import requests

from repo.provider_repo import (
    get_active_default_llm_provider,
    get_llm_provider_by_code,
)


class LLMClientError(Exception):
    """Raised when provider selection or provider call fails."""


@dataclass
class ResolvedLLMProvider:
    """
    Clean in-memory shape used by the adapter.

    Why:
    - Keeps later graph/node code simple.
    - Avoids passing raw DB rows everywhere.
    """

    provider_code: str
    provider_name: str
    provider_type: str
    base_url: Optional[str]
    auth_type: str
    api_key_env_var: Optional[str]
    model_name: str
    temperature: float
    max_tokens: int


@dataclass
class LLMTextResponse:
    """Normalized text response returned by this adapter."""

    provider_code: str
    provider_name: str
    model_name: str
    text: str
    raw_response: Any


# ---------------------------------------------------------------------
# Provider lookup / resolution
# ---------------------------------------------------------------------
def resolve_llm_provider(provider_code: Optional[str] = None) -> ResolvedLLMProvider:
    """
    Resolve provider configuration from DB.

    Rules:
    - If provider_code is provided, use that provider.
    - Else use active default provider.
    - Raise clear error if nothing is configured.
    """
    if provider_code:
        row = get_llm_provider_by_code(provider_code)
        if not row:
            raise LLMClientError(f"LLM provider '{provider_code}' is not configured or not active.")
    else:
        row = get_active_default_llm_provider()
        if not row:
            raise LLMClientError("No active default LLM provider is configured.")

    try:
        return ResolvedLLMProvider(
            provider_code=(row.get("provider_code") or "").strip().upper(),
            provider_name=(row.get("provider_name") or "").strip(),
            provider_type=(row.get("provider_type") or "").strip(),
            base_url=(row.get("base_url") or "").strip() or None,
            auth_type=(row.get("auth_type") or "").strip().upper(),
            api_key_env_var=(row.get("api_key_env_var") or "").strip() or None,
            model_name=(row.get("model_name") or "").strip(),
            temperature=float(row.get("temperature") or 0),
            max_tokens=int(row.get("max_tokens") or 1024),
        )
    except Exception as exc:
        raise LLMClientError(f"Invalid LLM provider configuration: {exc}") from exc


# ---------------------------------------------------------------------
# Public entry point used in later phases
# ---------------------------------------------------------------------
def generate_text(
    *,
    prompt: str,
    provider_code: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout_sec: int = 60,
) -> LLMTextResponse:
    """
    Provider-aware text generation entry point.

    Later usage idea:
        response = generate_text(prompt=prompt, provider_code='GEMINI')
        print(response.text)
    """
    provider = resolve_llm_provider(provider_code)

    resolved_temperature = provider.temperature if temperature is None else float(temperature)
    resolved_max_tokens = provider.max_tokens if max_tokens is None else int(max_tokens)

    if provider.provider_code == "GEMINI":
        return _generate_text_gemini(
            provider=provider,
            prompt=prompt,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            timeout_sec=timeout_sec,
        )

    if provider.provider_code == "OLLAMA":
        return _generate_text_ollama(
            provider=provider,
            prompt=prompt,
            temperature=resolved_temperature,
            max_tokens=resolved_max_tokens,
            timeout_sec=timeout_sec,
        )

    raise LLMClientError(
        f"Provider '{provider.provider_code}' is not supported yet in core/llm_client.py."
    )


# ---------------------------------------------------------------------
# GEMINI provider
# ---------------------------------------------------------------------
def _generate_text_gemini(
    *,
    provider: ResolvedLLMProvider,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
) -> LLMTextResponse:
    api_key = _read_required_api_key(provider)
    base_url = (provider.base_url or "https://generativelanguage.googleapis.com").rstrip("/")
    url = f"{base_url}/v1beta/models/{provider.model_name}:generateContent"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    _raise_for_http_error(resp, provider_code=provider.provider_code, provider_name=provider.provider_name)

    data = resp.json()
    text = _extract_gemini_text(data)

    return LLMTextResponse(
        provider_code=provider.provider_code,
        provider_name=provider.provider_name,
        model_name=provider.model_name,
        text=text,
        raw_response=data,
    )


# ---------------------------------------------------------------------
# OLLAMA provider
# ---------------------------------------------------------------------
def _generate_text_ollama(
    *,
    provider: ResolvedLLMProvider,
    prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_sec: int,
) -> LLMTextResponse:
    base_url = (provider.base_url or "http://127.0.0.1:11434").rstrip("/")
    url = f"{base_url}/api/generate"

    payload = {
        "model": provider.model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    headers = {"Content-Type": "application/json"}

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    _raise_for_http_error(resp, provider_code=provider.provider_code, provider_name=provider.provider_name)

    data = resp.json()
    text = (data.get("response") or "").strip()

    if not text:
        raise LLMClientError("OLLAMA returned an empty response.")

    return LLMTextResponse(
        provider_code=provider.provider_code,
        provider_name=provider.provider_name,
        model_name=provider.model_name,
        text=text,
        raw_response=data,
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _read_required_api_key(provider: ResolvedLLMProvider) -> str:
    if provider.auth_type == "NONE":
        return ""

    env_name = (provider.api_key_env_var or "").strip()
    if not env_name:
        raise LLMClientError(
            f"Provider '{provider.provider_code}' requires api_key_env_var in llm_provider table."
        )

    value = (os.getenv(env_name) or "").strip()
    if not value:
        raise LLMClientError(
            f"Environment variable '{env_name}' is not set for provider '{provider.provider_code}'."
        )

    return value



def _raise_for_http_error(resp: requests.Response, *, provider_code: str, provider_name: str) -> None:
    if resp.status_code < 400:
        return

    body = (resp.text or "").strip()
    if len(body) > 2000:
        body = body[:2000] + " ...[truncated]"

    raise LLMClientError(
        f"{provider_code} ({provider_name}) HTTP {resp.status_code}. Body={body}"
    )



def _extract_gemini_text(data: dict) -> str:
    """
    Extract plain text from Gemini generateContent response.

    We keep this tolerant because model responses may include multiple parts.
    """
    candidates = data.get("candidates") or []
    if not candidates:
        raise LLMClientError("GEMINI returned no candidates.")

    first = candidates[0] or {}
    content = first.get("content") or {}
    parts = content.get("parts") or []

    text_chunks: list[str] = []
    for part in parts:
        if isinstance(part, dict) and part.get("text"):
            text_chunks.append(str(part["text"]))

    text = "\n".join(chunk.strip() for chunk in text_chunks if chunk and chunk.strip()).strip()
    if not text:
        raise LLMClientError("GEMINI returned no text content.")

    return text



def response_to_json_text(response: LLMTextResponse) -> str:
    """
    Small helper for logging/debugging when needed later.
    """
    return json.dumps(
        {
            "provider_code": response.provider_code,
            "provider_name": response.provider_name,
            "model_name": response.model_name,
            "text": response.text,
        },
        ensure_ascii=False,
        indent=2,
    )
