"""Unit tests for Phase 3 v2 caching and hierarchical generation.

Fake LLM backend only — no network, no models, no datasets. Covers
requirements N11-N15 (hash identity, invalidation, resume safety, one-level
hierarchy, zero dry-run calls).
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from context_v2 import (                                     # noqa: E402
    HFTokenCounter, HierCache, HierLLM, PROMPT_VERSION, build_stage1_messages,
    build_stage2_messages, context_hash, generate_hierarchical,
    generation_settings_hash, load_token_counter, payload_hash, TokenizerAccessError,
    validate_generation_metadata, WhitespaceTokenCounter,
)

MODEL = "test/model"


class FakeBackend:
    """Deterministic fake; counts invocations so 'zero calls' is provable."""

    def __init__(self):
        self.calls = []

    def __call__(self, messages, temperature, max_tokens):
        self.calls.append({"messages": messages, "temperature": temperature,
                           "max_tokens": max_tokens})
        return f"RESPONSE[{len(self.calls)}]"


def mk_llm(tmp_path, dry_run=False):
    be = FakeBackend()
    return HierLLM(be, HierCache(tmp_path / "cache"), MODEL,
                   dry_run=dry_run), be


MSG = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hello"}]


# ---------------------------------------------------------------- N11
def test_identical_payloads_same_hash_and_one_cache_entry(tmp_path):
    llm, be = mk_llm(tmp_path)
    out1, h1 = llm.complete("stage1", MSG, 0.0, 256)
    out2, h2 = llm.complete("stage1", MSG, 0.0, 256)
    assert h1 == h2, "identical payloads must hash identically"
    assert out1 == out2
    assert len(be.calls) == 1, "second identical request must hit the cache"
    assert len(list((tmp_path / "cache").glob("*.json"))) == 1


def test_concurrent_identical_payloads_still_make_one_call(tmp_path):
    class SlowBackend(FakeBackend):
        def __call__(self, messages, temperature, max_tokens):
            time.sleep(0.02)
            return super().__call__(messages, temperature, max_tokens)

    be = SlowBackend()
    llm = HierLLM(be, HierCache(tmp_path / "cache"), MODEL)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(
            lambda _: llm.complete("stage1", MSG, 0.0, 256), range(4)))
    assert len({value[1] for value in results}) == 1
    assert len(be.calls) == 1
    assert llm.n_calls == 1


def test_same_prompt_across_conditions_reuses_one_brief(tmp_path):
    """Content-addressing means condition identity is irrelevant."""
    llm, be = mk_llm(tmp_path)
    blocks = ["[e1 | FOCAL | Article 1]\nsome text"]
    msgs = build_stage1_messages(blocks, "group 1")
    _, ha = llm.complete("stage1", msgs, 0.0, 256)      # as condition A
    _, hb = llm.complete("stage1", msgs, 0.0, 256)      # as condition B
    assert ha == hb
    assert len(be.calls) == 1


# ---------------------------------------------------------------- N12
@pytest.mark.parametrize("mutate", ["model", "prompt_version", "stage",
                                    "temperature", "max_tokens", "content"])
def test_changing_any_parameter_changes_hash(mutate):
    base = dict(model=MODEL, prompt_version=PROMPT_VERSION, stage="stage1",
                temperature=0.0, max_tokens=256, messages=MSG)
    h0 = payload_hash(**base)
    m = dict(base)
    if mutate == "content":
        m["messages"] = [{"role": "system", "content": "sys"},
                         {"role": "user", "content": "hello!"}]
    elif mutate == "temperature":
        m["temperature"] = 0.1
    elif mutate == "max_tokens":
        m["max_tokens"] = 257
    else:
        m[mutate] = "CHANGED"
    assert payload_hash(**m) != h0, f"changing {mutate} must invalidate the cache"


def test_provider_routing_changes_hierarchical_hash():
    base = dict(model=MODEL, prompt_version=PROMPT_VERSION, stage="stage1",
                temperature=0.0, max_tokens=256, messages=MSG)
    coreweave = payload_hash(**base, request_options={
        "provider": {"only": ["coreweave"], "quantizations": ["fp16"]}})
    deepinfra = payload_hash(**base, request_options={
        "provider": {"only": ["deepinfra"], "quantizations": ["fp8"]}})
    assert coreweave != deepinfra


# ---------------------------------------------------------------- N13
def test_resume_rejects_row_with_different_hashes(tmp_path):
    """A completed row is only reusable if its context AND prompt hashes match."""
    ctx_a = context_hash({0: ["u1", "u2"]}, budget=1800, n_groups=4)
    ctx_b = context_hash({0: ["u1", "u3"]}, budget=1800, n_groups=4)
    assert ctx_a != ctx_b

    existing = {"celex": "X", "cond": "A", "context_hash": ctx_a,
                "stage2_hash": "abc"}

    def can_resume(row, ctx_hash, s2_hash):
        return row["context_hash"] == ctx_hash and row["stage2_hash"] == s2_hash

    assert can_resume(existing, ctx_a, "abc")
    assert not can_resume(existing, ctx_b, "abc"), "different context must abort"
    assert not can_resume(existing, ctx_a, "zzz"), "different prompt must abort"


@pytest.mark.parametrize("field", ["model", "prompt_version", "temperature",
                                   "stage1_max_tokens", "final_max_tokens"])
def test_generation_settings_hash_invalidates_every_generation_setting(field):
    settings = dict(model=MODEL, prompt_version=PROMPT_VERSION, temperature=0.0,
                    stage1_max_tokens=256, final_max_tokens=1024)
    original = generation_settings_hash(**settings)
    changed = dict(settings)
    changed[field] = changed[field] + 1 if isinstance(changed[field], (int, float)) \
        else str(changed[field]) + "-changed"
    assert generation_settings_hash(**changed) != original


# ---------------------------------------------------------------- N14
def test_one_brief_per_nonempty_group_and_exactly_one_composition(tmp_path):
    llm, be = mk_llm(tmp_path)
    groups = [["blk a"], ["blk b"], [], ["blk d"]]        # group 3 empty
    out = generate_hierarchical(groups, llm)
    assert out["n_groups_used"] == 3, "empty groups must not produce a brief"
    assert len(out["stage1_hashes"]) == 3
    assert isinstance(out["stage2_hash"], str)
    stages = [c["max_tokens"] for c in be.calls]
    assert stages.count(256) == 3 and stages.count(1024) == 1
    assert len(be.calls) == 4, "3 briefs + exactly 1 composition"


def test_hierarchy_is_one_level_only(tmp_path):
    """No recursive re-summarisation: calls == non-empty groups + 1."""
    llm, be = mk_llm(tmp_path)
    groups = [["a"], ["b"], ["c"], ["d"]]
    generate_hierarchical(groups, llm)
    assert len(be.calls) == 5


# ---------------------------------------------------------------- N15
def test_dry_run_makes_zero_llm_calls(tmp_path):
    llm, be = mk_llm(tmp_path, dry_run=True)
    groups = [["a"], ["b"], ["c"], ["d"]]
    out = generate_hierarchical(groups, llm)
    assert len(be.calls) == 0, "dry-run must never invoke the backend"
    assert llm.n_calls == 0
    assert out["stage2_hash"], "hashes still computed for auditing"
    assert not list((tmp_path / "cache").glob("*.json")), "nothing cached"


def test_stage2_messages_contain_no_evidence_ids():
    msgs = build_stage2_messages(["note one [e1]", "note two [e2]"])
    sys_msg = msgs[0]["content"]
    assert "no headings" in sys_msg.lower() or "do not use headings" in sys_msg.lower()
    assert "evidence ids" in sys_msg.lower()


# ------------------------------------------------ tokenizer safety
def _blocked_tokenizer(_name):
    raise PermissionError("401 gated repository")


def test_exact_tokenizer_failure_is_closed_by_default():
    with pytest.raises(TokenizerAccessError):
        load_token_counter("gated/model", factory=_blocked_tokenizer)


def test_approximate_tokenizer_requires_dry_run_and_explicit_flag():
    with pytest.raises(TokenizerAccessError):
        load_token_counter("gated/model", allow_approximate=True,
                           dry_run=False, factory=_blocked_tokenizer)
    with pytest.raises(TokenizerAccessError):
        load_token_counter("gated/model", allow_approximate=False,
                           dry_run=True, factory=_blocked_tokenizer)
    tok = load_token_counter("gated/model", allow_approximate=True,
                             dry_run=True, factory=_blocked_tokenizer)
    assert isinstance(tok, WhitespaceTokenCounter)
    assert tok.provenance()["valid_for_generation"] is False


def test_generation_metadata_rejects_approximate_tokenizer():
    with pytest.raises(ValueError, match="not generation-ready"):
        validate_generation_metadata({
            "tokenizer": WhitespaceTokenCounter().provenance()})


def test_generation_metadata_requires_exact_provenance():
    exact = {
        "tokenizer_mode": "exact", "valid_for_generation": True,
        "repository": "model", "tokenizer_class": "FakeTokenizer",
        "counting_adapter_version": "hf-chat-template-input-ids-v2",
        "vocab_size": 10, "configuration_sha256": "a",
        "vocabulary_sha256": "b",
    }
    validate_generation_metadata({"tokenizer": exact})
    broken = dict(exact)
    broken["vocabulary_sha256"] = None
    with pytest.raises(ValueError, match="provenance missing"):
        validate_generation_metadata({"tokenizer": broken})


def test_hf_counter_extracts_input_ids_from_batch_encoding_like_result():
    """Regression: transformers 5 BatchEncoding length is field count, not tokens."""
    class FakeBatchEncoding:
        def __init__(self):
            self.data = {"input_ids": list(range(137)),
                         "attention_mask": [1] * 137}

        def get(self, key, default=None):
            return self.data.get(key, default)

        def __len__(self):
            return len(self.data)  # the old bug returned 2

    class FakeTokenizer:
        def apply_chat_template(self, *args, **kwargs):
            return FakeBatchEncoding()

    counter = HFTokenCounter.__new__(HFTokenCounter)
    counter._tok = FakeTokenizer()
    assert counter.count_messages([{"role": "user", "content": "hello"}]) == 137


def test_old_exact_metadata_without_fixed_counting_adapter_is_rejected():
    old = {
        "tokenizer_mode": "exact", "valid_for_generation": True,
        "repository": "model", "tokenizer_class": "FakeTokenizer",
        "vocab_size": 10, "configuration_sha256": "a",
        "vocabulary_sha256": "b",
    }
    with pytest.raises(ValueError, match="counting_adapter_version"):
        validate_generation_metadata({"tokenizer": old})
