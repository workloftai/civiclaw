"""
civiclaw model router.

Skills call `router.chat(system, user, model_tier=...)` instead of hard-wiring
Anthropic, OpenAI, or any other SDK. The router picks a backend based on:

  1. CIVICLAW_MODEL environment variable, if set (wins)
  2. the model_tier declared by the skill ("cheap" / "mid" / "frontier")
  3. default preference order: anthropic → openai → gemini → ollama

If the preferred backend's credentials are missing, the router falls back to
the next one. The final fallback is always `ollama` on localhost, which lets a
council run civiclaw with zero US-lab dependency.

This file is intentionally dependency-light. It imports Anthropic only if it's
used and falls back to `urllib` for everything else.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Callable


DEFAULT_MODELS = {
    "anthropic": {
        "cheap": "claude-haiku-4-5",
        "mid": "claude-sonnet-4-6",
        "frontier": "claude-opus-4-7",
    },
    "openai": {"cheap": "gpt-4o-mini", "mid": "gpt-4o", "frontier": "gpt-5"},
    "gemini": {"cheap": "gemini-flash-3.1", "mid": "gemini-pro-3.1", "frontier": "gemini-ultra"},
    "ollama": {"cheap": "qwen2.5:3b", "mid": "qwen2.5:7b-instruct-q4_K_M", "frontier": "qwen2:72b"},
}

PREFERENCE_ORDER = ["anthropic", "openai", "gemini", "ollama"]


@dataclass
class ModelResponse:
    text: str
    backend: str
    model: str


def _have_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _have_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _have_gemini() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def _have_ollama() -> bool:
    # Assume Ollama is running locally if OLLAMA_HOST is set or :11434 is reachable.
    if os.environ.get("OLLAMA_HOST"):
        return True
    try:
        import socket

        with socket.create_connection(("127.0.0.1", 11434), timeout=0.25):
            return True
    except OSError:
        return False


BACKEND_CHECKS: dict[str, Callable[[], bool]] = {
    "anthropic": _have_anthropic,
    "openai": _have_openai,
    "gemini": _have_gemini,
    "ollama": _have_ollama,
}


def _pick_backend(forced: str | None) -> str:
    if forced:
        if forced not in DEFAULT_MODELS:
            raise ValueError(f"unknown backend: {forced}")
        if not BACKEND_CHECKS[forced]():
            raise RuntimeError(f"backend {forced} forced via CIVICLAW_MODEL but not available")
        return forced
    for backend in PREFERENCE_ORDER:
        if BACKEND_CHECKS[backend]():
            return backend
    raise RuntimeError("no model backend available — set ANTHROPIC_API_KEY or run Ollama on :11434")


def _chat_anthropic(system: str, user: str, model: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text  # type: ignore[attr-defined]


def _chat_openai(system: str, user: str, model: str, max_tokens: int) -> str:
    import urllib.request

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read())
    return body["choices"][0]["message"]["content"]


def _chat_gemini(system: str, user: str, model: str, max_tokens: int) -> str:
    import urllib.request

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ["GOOGLE_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read())
    return body["candidates"][0]["content"]["parts"][0]["text"]


def _chat_ollama(system: str, user: str, model: str, max_tokens: int) -> str:
    import urllib.request

    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    req = urllib.request.Request(
        f"{host.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    return body["message"]["content"]


CHAT_IMPLS = {
    "anthropic": _chat_anthropic,
    "openai": _chat_openai,
    "gemini": _chat_gemini,
    "ollama": _chat_ollama,
}


def chat(system: str, user: str, *, model_tier: str = "mid", max_tokens: int = 2048) -> ModelResponse:
    """Single entry point for skills. Picks a backend, calls it, returns text + metadata."""
    forced = os.environ.get("CIVICLAW_MODEL")
    backend = _pick_backend(forced)
    model = DEFAULT_MODELS[backend][model_tier]
    text = CHAT_IMPLS[backend](system, user, model, max_tokens)
    return ModelResponse(text=text, backend=backend, model=model)


def chat_text(system: str, user: str, *, model_tier: str = "mid", max_tokens: int = 2048) -> str:
    """Plain-text convenience wrapper used by skills that don't need backend metadata."""
    return chat(system, user, model_tier=model_tier, max_tokens=max_tokens).text


if __name__ == "__main__":
    # Print which backend would be used without making a call.
    forced = os.environ.get("CIVICLAW_MODEL")
    try:
        backend = _pick_backend(forced)
        print(f"civiclaw router would use: {backend} (tier=mid → {DEFAULT_MODELS[backend]['mid']})")
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
