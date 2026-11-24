import hashlib
import json
import time
from typing import Any
import litellm
from litellm import Cache
from .config import settings

# LiteLLM's built-in local cache is enabled. The small response cache below
# makes cache-hit metadata deterministic and guarantees the assignment's
# exact cache-key behavior across new sessions in this single-worker app.
litellm.cache = Cache(type="local")
_RESPONSE_CACHE: dict[str, dict[str, Any]] = {}

def _cache_key(messages: list[dict], model: str) -> str:
    canonical = json.dumps(
        {"model": model, "messages": messages},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def _simulated_failures(header: str | None) -> dict[str, int]:
    failures = {}
    if not header:
        return failures
    for part in header.split(","):
        if "=" not in part:
            continue
        key_id, status = part.strip().split("=", 1)
        try:
            status_code = int(status)
        except ValueError:
            continue
        if status_code in {429, 500, 502, 503}:
            failures[key_id.strip()] = status_code
    return failures

def _extract_usage(response) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    prompt = getattr(usage, "prompt_tokens", None) if usage else None
    completion = getattr(usage, "completion_tokens", None) if usage else None
    # Some providers expose these under input_tokens/output_tokens.
    if prompt is None and usage:
        prompt = getattr(usage, "input_tokens", 0)
    if completion is None and usage:
        completion = getattr(usage, "output_tokens", 0)
    return int(prompt or 0), int(completion or 0)

async def generate_reply(messages: list[dict], simulate_header: str | None = None) -> tuple[str, dict]:
    if len(settings.llm_api_keys) < 2:
        raise RuntimeError("Configure at least two keys in LLM_API_KEYS")

    key = _cache_key(messages, settings.model)
    started = time.perf_counter()

    cached = _RESPONSE_CACHE.get(key)
    if cached is not None:
        metadata = {
            **cached["metadata"],
            "resolution_source": "LLM_CACHE",
            "latency_ms": max(0, int((time.perf_counter() - started) * 1000)),
            "key_id": None,
            "fallback_attempts": 0,
        }
        return cached["reply"], metadata

    simulated = _simulated_failures(simulate_header) if settings.enable_failure_simulation else {}
    failures = 0
    last_error = None

    for index, api_key in enumerate(settings.llm_api_keys):
        key_id = f"key_{index + 1}"
        if "*" in simulated or key_id in simulated:
            failures += 1
            last_error = RuntimeError(f"Simulated provider failure: {simulated.get(key_id, simulated.get('*'))}")
            continue
        try:
            response = await litellm.acompletion(
                model=settings.model,
                api_key=api_key,
                messages=messages,
                caching=True,
                num_retries=0,
                timeout=45,
            )
            reply = response.choices[0].message.content
            if isinstance(reply, list):
                reply = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in reply
                )
            reply = (reply or "").strip()
            if not reply:
                raise RuntimeError("The model returned an empty response")

            input_tokens, output_tokens = _extract_usage(response)
            latency = max(0, int((time.perf_counter() - started) * 1000))
            metadata = {
                "resolution_source": "LIVE_INFERENCE",
                "model": settings.model,
                "latency_ms": latency,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": key_id,
                "fallback_attempts": failures,
            }
            _RESPONSE_CACHE[key] = {
                "reply": reply,
                "metadata": {
                    "model": settings.model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            }
            return reply, metadata
        except Exception as exc:
            print(f"Provider {key_id} failed: {type(exc).__name__}: {exc}")
            last_error = exc
            failures += 1
            # Continue to the next configured key for rate limits, quota,
            # provider/server errors, auth errors, and transient failures.

    raise RuntimeError("all providers unavailable") from last_error
