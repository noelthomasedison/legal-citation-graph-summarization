"""Offline tests for the blinded legal/user summary judge."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from llm_summary_judge_v2 import (  # noqa: E402
    CONDITIONS, DIMENSIONS, HEADLINE_SCORES, blinded_candidates, build_messages, macro_score,
    response_schema, validate_judgement,
)


def valid_response():
    return {"evaluations": [{
        "candidate_id": cid,
        "scores": {name: 4 for name in DIMENSIONS},
        "headline_scores": {name: 4 for name in HEADLINE_SCORES},
        "material_error": False, "material_omission": False,
        "not_confirmed_by_reference": False,
        "rationale": "Accurate, useful and concise.",
    } for cid in ("S1", "S2", "S3", "S4")]}


def test_blinding_is_complete_deterministic_and_act_specific():
    summaries = {cond: f"text-{cond}" for cond in CONDITIONS}
    one, mapping_one = blinded_candidates("ACT-1", summaries, seed=41)
    two, mapping_two = blinded_candidates("ACT-1", summaries, seed=41)
    assert one == two and mapping_one == mapping_two
    assert set(mapping_one.values()) == set(CONDITIONS)
    assert all(cond not in one for cond in CONDITIONS)
    assert blinded_candidates("ACT-2", summaries, seed=41)[1] != mapping_one


def test_prompt_contains_gold_and_candidates_but_not_condition_names():
    candidates = {f"S{i}": f"candidate text {i}" for i in range(1, 5)}
    messages = build_messages("32000R0001", "gold reference", candidates)
    user = messages[1]["content"]
    assert "gold reference" in user
    assert all(text in user for text in candidates.values())
    assert '"base"' not in user and '"oracle"' not in user


def test_schema_is_strict_and_covers_all_dimensions():
    schema = response_schema(["S1", "S2", "S3", "S4"])
    assert schema["additionalProperties"] is False
    props = schema["properties"]["evaluations"]["items"]["properties"]
    assert set(props["scores"]["properties"]) == set(DIMENSIONS)
    assert set(props["headline_scores"]["properties"]) == set(HEADLINE_SCORES)


def test_validation_and_macro_score():
    clean = validate_judgement(valid_response(), ["S1", "S2", "S3", "S4"])
    assert macro_score(clean["evaluations"][0]) == 4.0


def test_validation_drops_harmless_provider_wrapper_metadata():
    value = valid_response()
    value["provider_note"] = "wrapper field not part of persisted result"
    clean = validate_judgement(value, ["S1", "S2", "S3", "S4"])
    assert set(clean) == {"evaluations"}


def test_validation_rejects_duplicate_candidate():
    value = valid_response()
    value["evaluations"][3]["candidate_id"] = "S1"
    with pytest.raises(ValueError, match="unique"):
        validate_judgement(value, ["S1", "S2", "S3", "S4"])


def test_validation_rejects_boolean_or_out_of_range_score():
    value = valid_response()
    value["evaluations"][0]["scores"]["legal_fidelity"] = True
    with pytest.raises(ValueError, match="integer"):
        validate_judgement(value, ["S1", "S2", "S3", "S4"])
    value = valid_response()
    value["evaluations"][0]["scores"]["concision"] = 6
    with pytest.raises(ValueError, match="integer"):
        validate_judgement(value, ["S1", "S2", "S3", "S4"])
