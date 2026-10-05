"""Offline tests for provider isolation and transport provenance."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from citation_evidence_v2 import StructuredCache, StructuredLLM, validate_need  # noqa: E402
from llm_provider_v2 import (                               # noqa: E402
    BackendResponse, RetryableProviderResponseError, chat_completion_text,
    load_api_key, resolve_inference_config,
    response_metadata,
)


def test_openrouter_defaults_pin_coreweave_fp16_without_fallbacks():
    config = resolve_inference_config("openrouter")
    assert config.model == "meta-llama/llama-3.3-70b-instruct"
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.request_options() == {
        "provider": {
            "only": ["coreweave"],
            "allow_fallbacks": False,
            "require_parameters": True,
            "quantizations": ["fp16"],
        }
    }


def test_low_precision_openrouter_quantization_is_rejected():
    with pytest.raises(ValueError, match="quantization"):
        resolve_inference_config("openrouter", quantization="int4")


def test_native_gpt_oss_fp4_quantization_is_recorded():
    config = resolve_inference_config(
        "openrouter", model="openai/gpt-oss-120b", quantization="fp4")
    assert config.request_options()["provider"]["quantizations"] == ["fp4"]


def test_provider_and_routing_are_public_but_key_never_is(tmp_path):
    config = resolve_inference_config("openrouter")
    key_file = tmp_path / ".openrouter_api_key"
    key_file.write_text("secret-from-file")
    key, source = load_api_key(config, tmp_path, environ={})
    assert key == "secret-from-file"
    assert source == ".openrouter_api_key"
    assert "secret" not in str(config.public_record())


def test_openrouter_environment_key_takes_precedence(tmp_path):
    config = resolve_inference_config("openrouter")
    (tmp_path / ".openrouter_api_key").write_text("file-secret")
    key, source = load_api_key(
        config, tmp_path, environ={"OPENROUTER_API_KEY": "env-secret"})
    assert key == "env-secret"
    assert source == "OPENROUTER_API_KEY"


def test_response_metadata_records_actual_provider_and_usage():
    config = resolve_inference_config("openrouter")
    meta = response_metadata({
        "id": "gen-1", "model": config.model, "provider": "CoreWeave",
        "created": 123, "usage": {"prompt_tokens": 10,
                                    "completion_tokens": 4,
                                    "total_tokens": 14},
    }, config)
    assert meta["actual_provider"] == "CoreWeave"
    assert meta["configured_quantization"] == "fp16"
    assert meta["usage"]["total_tokens"] == 14


def test_chat_completion_text_validates_provider_wrapper():
    assert chat_completion_text({
        "choices": [{"message": {"content": "  result  "}}]
    }) == "result"
    with pytest.raises(RetryableProviderResponseError, match="no chat completion"):
        chat_completion_text({"error": {"message": "temporary upstream miss"}})
    with pytest.raises(RetryableProviderResponseError, match="empty"):
        chat_completion_text({"choices": [{"message": {"content": ""}}]})


def test_structured_cache_retains_transport_provenance(tmp_path):
    transport = {"gateway": "openrouter", "actual_provider": "CoreWeave"}
    backend = lambda *args: BackendResponse(
        '{"need_type":"none","question":"","required_fields":[],"status":"not_needed"}',
        transport)
    llm = StructuredLLM(
        backend, StructuredCache(tmp_path), "meta-llama/test",
        request_options={"provider": {"only": ["coreweave"]}})
    _, request_hash = llm.complete("need", "v1", [], 20, validate_need)
    assert llm.transport_for(request_hash) == transport


def test_routing_configuration_changes_structured_cache_identity(tmp_path):
    response = '{"need_type":"none","question":"","required_fields":[],"status":"not_needed"}'
    one = StructuredLLM(
        lambda *args: response, StructuredCache(tmp_path / "one"), "same-model",
        request_options={"provider": {"only": ["coreweave"]}})
    two = StructuredLLM(
        lambda *args: response, StructuredCache(tmp_path / "two"), "same-model",
        request_options={"provider": {"only": ["deepinfra"]}})
    _, hash_one = one.complete("need", "v1", [], 20, validate_need)
    _, hash_two = two.complete("need", "v1", [], 20, validate_need)
    assert hash_one != hash_two
