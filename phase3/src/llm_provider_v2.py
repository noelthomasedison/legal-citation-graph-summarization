"""Auditable inference-provider configuration for Phase 3 v2.

The provider is part of request/cache identity.  Secrets are loaded locally
and are never included in public records, caches, or manifests.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"


@dataclass(frozen=True)
class BackendResponse:
    """Text plus non-secret transport provenance returned by a chat backend."""

    text: str
    metadata: dict


class RetryableProviderResponseError(ValueError):
    """A successful HTTP response did not contain a usable chat completion."""


def chat_completion_text(response: dict) -> str:
    """Extract non-empty chat text, classifying provider wrapper failures."""
    choices = response.get("choices") if isinstance(response, dict) else None
    if not isinstance(choices, list) or not choices:
        error = response.get("error") if isinstance(response, dict) else None
        if isinstance(error, dict):
            detail = str(error.get("message") or error.get("code") or "unknown error")
        else:
            detail = "missing choices"
        raise RetryableProviderResponseError(
            f"provider returned no chat completion ({detail[:160]})")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RetryableProviderResponseError("provider returned empty chat content")
    return content.strip()


@dataclass(frozen=True)
class InferenceConfig:
    gateway: str
    base_url: str
    model: str
    endpoint_provider: str | None
    quantization: str | None
    allow_fallbacks: bool

    def request_options(self) -> dict:
        """Provider-specific request body; also included in cache identity."""
        if self.gateway != "openrouter":
            return {}
        provider = {
            "only": [self.endpoint_provider],
            "allow_fallbacks": self.allow_fallbacks,
            "require_parameters": True,
        }
        if self.quantization:
            provider["quantizations"] = [self.quantization]
        return {"provider": provider}

    def public_record(self) -> dict:
        return {
            "gateway": self.gateway,
            "base_url": self.base_url,
            "model": self.model,
            "endpoint_provider": self.endpoint_provider,
            "quantization": self.quantization,
            "allow_fallbacks": self.allow_fallbacks,
            "request_options": self.request_options(),
        }


def resolve_inference_config(
    gateway: str,
    model: str | None = None,
    endpoint_provider: str = "coreweave",
    quantization: str = "fp16",
    allow_fallbacks: bool = False,
) -> InferenceConfig:
    gateway = gateway.lower().strip()
    if gateway == "nvidia":
        if endpoint_provider != "coreweave" or quantization != "fp16" or allow_fallbacks:
            # These are OpenRouter controls.  Silently accepting them for
            # NVIDIA would make the recorded configuration misleading.
            raise ValueError("OpenRouter routing controls require --provider openrouter")
        return InferenceConfig(
            gateway="nvidia",
            base_url="https://integrate.api.nvidia.com/v1",
            model=model or NVIDIA_MODEL,
            endpoint_provider=None,
            quantization=None,
            allow_fallbacks=False,
        )
    if gateway != "openrouter":
        raise ValueError("provider must be 'nvidia' or 'openrouter'")
    endpoint_provider = endpoint_provider.lower().strip()
    quantization = quantization.lower().strip()
    if not endpoint_provider:
        raise ValueError("OpenRouter requires one pinned endpoint provider")
    if quantization not in {"fp4", "mxfp4", "fp8", "fp16", "bf16", "fp32"}:
        raise ValueError(
            "OpenRouter quantization must be fp4, mxfp4, fp8, fp16, bf16 or fp32")
    return InferenceConfig(
        gateway="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model=model or OPENROUTER_MODEL,
        endpoint_provider=endpoint_provider,
        quantization=quantization,
        allow_fallbacks=bool(allow_fallbacks),
    )


def load_api_key(config: InferenceConfig, phase1_root: Path,
                 environ: dict | None = None) -> tuple[str | None, str]:
    """Return the secret and a safe description of where it came from."""
    env = os.environ if environ is None else environ
    if config.gateway == "openrouter":
        if env.get("OPENROUTER_API_KEY"):
            return env["OPENROUTER_API_KEY"], "OPENROUTER_API_KEY"
        key_file = Path(phase1_root) / ".openrouter_api_key"
    else:
        if env.get("NVIDIA_API_KEY"):
            return env["NVIDIA_API_KEY"], "NVIDIA_API_KEY"
        key_file = Path(phase1_root) / ".nvidia_api_key"
    if key_file.exists():
        return key_file.read_text().strip(), key_file.name
    return None, "missing"


def response_metadata(response: dict, config: InferenceConfig) -> dict:
    """Extract reproducibility metadata without retaining prompts or secrets."""
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    return {
        "gateway": config.gateway,
        "configured_endpoint_provider": config.endpoint_provider,
        "actual_provider": response.get("provider"),
        "configured_quantization": config.quantization,
        "response_model": response.get("model"),
        "response_id": response.get("id"),
        "created": response.get("created"),
        "usage": {
            key: usage.get(key)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            if usage.get(key) is not None
        },
    }


def unpack_backend_response(value) -> tuple[str, dict]:
    """Keep existing fake/string backends compatible with provenance backends."""
    if isinstance(value, BackendResponse):
        return value.text, dict(value.metadata)
    if isinstance(value, str):
        return value, {}
    raise TypeError("LLM backend must return str or BackendResponse")
