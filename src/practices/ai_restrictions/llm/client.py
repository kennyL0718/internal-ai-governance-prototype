"""Minimal DeepSeek chat-completions client; credentials never enter metadata."""
from __future__ import annotations

import json
import http.client
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

PROVIDER = "DeepSeek"
MODEL = "deepseek-flash"
INTENDED_MODEL_VERSION = "DeepSeek-V4.1-Flash"
BASE_URL = "https://api.deepseek.com"


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str = field(repr=False)
    timeout_seconds: int = 120
    max_retries: int = 3

    @property
    def metadata(self) -> dict:
        return {"provider": PROVIDER, "model": MODEL, "intended_model_version": INTENDED_MODEL_VERSION, "base_url": BASE_URL, "timeout_seconds": self.timeout_seconds, "max_retries": self.max_retries}


def _local_env_key(path: Path) -> str | None:
    if not path.is_file():
        return None
    matches = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:].strip()
        name, separator, value = stripped.partition("=")
        if separator and name.strip() == "DEEPSEEK_API_KEY":
            matches.append(value.strip().strip('"').strip("'"))
    if len(matches) > 1:
        raise ValueError("Duplicate DEEPSEEK_API_KEY entries in local .env")
    return matches[0] if matches else None


def credential_detected(env_file: Path | None = None) -> bool:
    return bool(os.getenv("DEEPSEEK_API_KEY") or (env_file and _local_env_key(env_file)))


def load_config(env_file: Path | None = None) -> DeepSeekConfig:
    key = os.getenv("DEEPSEEK_API_KEY") or (env_file and _local_env_key(env_file))
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    return DeepSeekConfig(api_key=key)


def build_payload(system: str, user: str, *, max_tokens: int = 4096) -> dict:
    if not system or not user or max_tokens < 1:
        raise ValueError("System, user and positive max_tokens are required")
    return {"model": MODEL, "temperature": 0, "max_tokens": max_tokens, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}


def _transport(url: str, body: bytes, headers: dict, timeout: int) -> dict:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def chat_json(
    system: str, user: str, *, config: DeepSeekConfig,
    max_tokens: int = 4096,
    transport: Callable[[str, bytes, dict, int], dict] = _transport,
    sleep: Callable[[float], None] = time.sleep,
    attempt_observer: Callable[[dict], None] | None = None,
    response_observer: Callable[[dict], None] | None = None,
) -> tuple[dict, dict]:
    """Return parsed JSON and nonsecret call metadata. Retry transient failures."""
    payload = build_payload(system, user, max_tokens=max_tokens)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": "Bearer " + config.api_key, "Content-Type": "application/json"}
    for attempt in range(config.max_retries + 1):
        if attempt_observer:
            attempt_observer({'attempt': attempt, 'status': 'started'})
        try:
            response = transport(BASE_URL + "/chat/completions", body, headers, config.timeout_seconds)
            if response_observer:
                response_observer(response)
            usage = response.get("usage") or {}
            if attempt_observer:
                attempt_observer({'attempt': attempt, 'status': 'response_received', 'token_usage': usage, 'returned_model': response.get('model', ''), 'finish_reason': (response.get('choices') or [{}])[0].get('finish_reason')})
            choice = response["choices"][0]
            content = choice["message"]["content"]
            if choice.get("finish_reason") == "length" or not content:
                raise ValueError("Empty or truncated JSON response")
            result = json.loads(content)
            if not isinstance(result, dict):
                raise ValueError("JSON response is not an object")
            usage = response.get("usage") or {}
            metadata = {**config.metadata, "returned_model": response.get("model", ""), "request_status": "success", "cache_status": "miss", "retry_count": attempt, "max_tokens": max_tokens, "finish_reason": choice.get("finish_reason"), "token_usage": {name: usage.get(name) for name in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens") if usage.get(name) is not None}}
            if attempt_observer:
                attempt_observer({'attempt': attempt, 'status': 'success'})
            return result, metadata
        except urllib.error.HTTPError as exc:
            if attempt_observer:
                attempt_observer({'attempt': attempt, 'status': 'failure', 'error': f'HTTP {exc.code}'})
            if exc.code not in (429, 500, 502, 503, 504) or attempt == config.max_retries:
                raise RuntimeError(f"DeepSeek HTTP {exc.code}") from None
        except (urllib.error.URLError, http.client.HTTPException, TimeoutError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            if attempt_observer:
                attempt_observer({'attempt': attempt, 'status': 'failure', 'error': type(exc).__name__})
            if attempt == config.max_retries:
                raise RuntimeError("DeepSeek request or structured JSON parsing failed") from None
        sleep(min(2 ** (attempt + 1), 8))
    raise RuntimeError("DeepSeek retries exhausted")


def smoke_test(config: DeepSeekConfig) -> dict:
    """Tiny paid call, to be invoked only after the user configures the key."""
    result, metadata = chat_json(
        'Return a JSON object exactly like {"label":"test"}.',
        'Classify this test sentence as JSON: "This is a test."',
        config=config, max_tokens=64,
    )
    if not isinstance(result.get("label"), str):
        raise ValueError("Smoke test JSON schema was not satisfied")
    return metadata
