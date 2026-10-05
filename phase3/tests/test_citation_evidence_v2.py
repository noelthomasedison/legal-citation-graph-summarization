"""Offline tests for the fixed citation-conditioned evidence workflow."""
import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from citation_evidence_v2 import (                         # noqa: E402
    EXTRACT_PROMPT_VERSION, CitationRequest, StructuredCache, StructuredLLM,
    StructuredResponseError,
    build_extraction_messages, build_need_messages, card_is_usable,
    citation_source_context, deterministic_need, llm_payload_hash,
    parse_json_object, request_id,
    validate_extraction, validate_judgement,
    validate_extraction_for_need, validate_need,
)
from context_v2 import Candidate, WITHIN, render_block       # noqa: E402
from regkg.llm_extract import LLMClient                       # noqa: E402
import regkg.llm_extract as llm_module                        # noqa: E402


def fixture_request():
    return CitationRequest(
        request_id=request_id("src", "tgt", WITHIN), celex="ACT",
        scope=WITHIN, group=1, source_uid="src", source_doc="ACT",
        source_path=("65", "2"),
        source_text="The application shall follow the procedure in Article 66.",
        target_uid="tgt", target_doc="ACT", target_path=("66",),
        target_text=("The Agency shall assess the application within 30 days. "
                     "It may request additional information."),
    )


def test_request_id_binds_source_target_and_scope():
    assert request_id("s", "t", WITHIN) == request_id("s", "t", WITHIN)
    assert request_id("s", "t", WITHIN) != request_id("s2", "t", WITHIN)
    assert request_id("s", "t", WITHIN) != request_id("s", "t", "CITED_OTHER")


def test_public_workflow_cannot_accept_gold_summary():
    for fn in (build_need_messages, build_extraction_messages):
        params = set(inspect.signature(fn).parameters)
        assert not params & {"gold", "gold_summary", "summary", "reference"}


def test_need_is_structured_and_not_an_answer():
    need = validate_need({
        "need_type": "procedure", "question": "What procedure applies?",
        "required_fields": ["deadline", "responsible actor"],
        "status": "needed",
    })
    assert need["status"] == "needed"
    assert need["need_type"] == "procedure"
    messages = build_need_messages(fixture_request())
    assert "TARGET PROVISION" not in messages[1]["content"], \
        "need analyser must not see the target answer text"


def test_need_prompt_is_anchored_to_exact_resolver_mention():
    req = CitationRequest(**{
        **fixture_request().__dict__,
        "citation_mentions": ("Article 66",),
        "resolution_methods": ("exact",),
        "citation_keywords": ("Article",),
    })
    prompt = build_need_messages(req)[1]["content"]
    assert "RESOLVED CITATION MENTION" in prompt
    assert "Article 66" in prompt
    assert req.target_text not in prompt


def test_need_prompt_uses_local_context_for_a_long_source():
    req = CitationRequest(**{
        **fixture_request().__dict__,
        "source_text": "irrelevant " * 500 + "See Article 66 for timing. " +
                       "more irrelevant " * 500,
        "citation_mentions": ("Article 66",),
    })
    context = citation_source_context(req)
    assert "Article 66" in context
    assert len(context) < len(req.source_text) / 2
    assert context in build_need_messages(req)[1]["content"]


def test_common_composite_need_type_is_normalised_not_dropped():
    need = validate_need({
        "need_type": "threshold|scope",
        "question": "What annual amount applies?",
        "required_fields": ["annual amount"],
        "status": "needed",
    })
    assert need["need_type"] == "threshold"
    assert need["status"] == "needed"


def test_quoted_amendment_is_deterministically_self_contained():
    req = CitationRequest(**{
        **fixture_request().__dict__,
        "source_text": (
            "4. in Article 6(1), the first subparagraph shall be replaced by "
            "the following: ‘No medicinal product may be placed on the market.’"),
    })
    need = deterministic_need(req)
    assert need is not None
    assert need["status"] == "not_needed"


def test_cross_reference_without_quoted_amendment_still_uses_llm_need():
    assert deterministic_need(fixture_request()) is None


def test_not_needed_is_canonical_abstention():
    need = validate_need({"need_type": "other", "question": "ignored",
                          "required_fields": ["ignored"],
                          "status": "not_needed"})
    assert need == {"need_type": "none", "question": "",
                    "required_fields": [], "status": "not_needed"}


def test_supported_extraction_requires_verbatim_target_spans():
    req = fixture_request()
    good = validate_extraction({
        "status": "supported",
        "evidence": "The Agency has a 30-day assessment period.",
        "support_spans": ["The Agency shall assess the application within 30 days."],
    }, req.target_text)
    assert good["status"] == "supported"
    assert good["evidence"] == (
        "The Agency shall assess the application within 30 days.")
    assert good["model_evidence"] == (
        "The Agency has a 30-day assessment period.")
    with pytest.raises(ValueError, match="not verbatim"):
        validate_extraction({
            "status": "supported", "evidence": "It has 60 days.",
            "support_spans": ["The Agency has 60 days."],
        }, req.target_text)


def test_nonverbatim_span_becomes_fail_closed_abstention_in_pipeline():
    req = fixture_request()
    need = validate_need({
        "need_type": "procedure", "question": "What deadline applies?",
        "required_fields": ["deadline"], "status": "needed",
    })
    out = validate_extraction_for_need({
        "status": "supported", "evidence": "The deadline is thirty days.",
        "support_spans": ["The deadline is thirty days."],
    }, req.target_text, need)
    assert out["status"] == "insufficient_evidence"
    assert "not verbatim" in out["validation_reason"]


def test_insufficient_extraction_cannot_smuggle_text():
    value = validate_extraction({
        "status": "insufficient_evidence", "evidence": "invented",
        "support_spans": ["invented"],
    }, fixture_request().target_text)
    assert value == {"status": "insufficient_evidence", "evidence": "",
                     "support_spans": []}


def test_permission_cannot_pass_as_an_obligation():
    target = ("Member States shall have the right to decide the extent of support. "
              "Member States may open participation to producers.")
    need = validate_need({
        "need_type": "obligation", "question": "What obligations apply?",
        "required_fields": ["duties"], "status": "needed",
    })
    out = validate_extraction_for_need({
        "status": "supported",
        "evidence": ("Member States shall have the right to decide and may "
                     "open participation."),
        "support_spans": [
            "Member States shall have the right to decide the extent of support.",
            "Member States may open participation to producers.",
        ],
    }, target, need)
    assert out["status"] == "insufficient_evidence"
    assert "mandatory duty" in out["validation_reason"]


def test_real_shall_duty_can_reach_the_judge():
    target = "The relevant Member States shall agree on participation principles."
    need = validate_need({
        "need_type": "obligation", "question": "What obligations apply?",
        "required_fields": ["duties"], "status": "needed",
    })
    out = validate_extraction_for_need({
        "status": "supported", "evidence": target,
        "support_spans": [target],
    }, target, need)
    assert out["status"] == "supported"


def test_recommendation_cannot_be_grouped_as_a_decision():
    target = (
        "The Commission shall recommend that the Council impose a fine. "
        "The decision imposing a fine shall be deemed adopted by the Council.")
    need = validate_need({
        "need_type": "definition",
        "question": "What decisions are taken pursuant to Article 6?",
        "required_fields": ["decisions"], "status": "needed",
    })
    out = validate_extraction_for_need({
        "status": "supported",
        "evidence": (
            "The decisions include the Commission's recommendation to impose "
            "a fine and the Council's decision imposing the fine."),
        "support_spans": [
            "The Commission shall recommend that the Council impose a fine.",
            "The decision imposing a fine shall be deemed adopted by the Council.",
        ],
    }, target, need)
    assert out["status"] == "insufficient_evidence"
    assert "grouped as a decision" in out["validation_reason"]


def test_recommendation_may_be_labelled_as_procedural_precursor():
    target = (
        "The Commission shall recommend that the Council impose a fine. "
        "The decision imposing a fine shall be deemed adopted by the Council.")
    need = validate_need({
        "need_type": "procedure",
        "question": "How is the decision to impose a fine adopted?",
        "required_fields": ["recommendation", "decision"], "status": "needed",
    })
    out = validate_extraction_for_need({
        "status": "supported",
        "evidence": (
            "The Commission first makes a recommendation; the Council's "
            "decision imposing the fine is then deemed adopted."),
        "support_spans": [
            "The Commission shall recommend that the Council impose a fine.",
            "The decision imposing a fine shall be deemed adopted by the Council.",
        ],
    }, target, need)
    assert out["status"] == "supported"


def test_obligation_prompt_locates_duties_but_not_shall_have_right():
    req = fixture_request()
    req = CitationRequest(**{
        **req.__dict__,
        "target_text": ("Member States shall have the right to decide. "
                        "The relevant Member States shall agree on principles. "
                        "They may open participation."),
    })
    need = validate_need({
        "need_type": "obligation", "question": "What duties apply?",
        "required_fields": ["duties"], "status": "needed",
    })
    prompt = build_extraction_messages(req, need)[1]["content"]
    locator = prompt.split("MANDATORY-DUTY LOCATOR", 1)[1]
    assert "shall agree on principles" in locator
    assert "shall have the right" not in locator


def test_decision_prompt_locates_decision_sentences():
    req = fixture_request()
    req = CitationRequest(**{
        **req.__dict__,
        "target_text": (
            "The Commission shall make a recommendation. "
            "The Council adopts the final decision within three months."),
    })
    need = validate_need({
        "need_type": "procedure",
        "question": "How is the decision adopted?",
        "required_fields": ["decision", "deadline"],
        "status": "needed",
    })
    prompt = build_extraction_messages(req, need)[1]["content"]
    locator = prompt.split("DECISION LOCATOR", 1)[1]
    assert "adopts the final decision within three months" in locator
    assert "make a recommendation" not in locator


def test_judge_verdict_must_match_boolean_fields():
    assert validate_judgement({
        "verdict": "pass", "supported": True, "answers_need": True,
        "reason": "fully grounded",
    })["verdict"] == "pass"
    with pytest.raises(ValueError, match="conflicts"):
        validate_judgement({
            "verdict": "pass", "supported": False, "answers_need": True,
            "reason": "contradiction",
        })


def test_only_independently_passed_supported_card_is_usable():
    base = {"status": "supported", "evidence": "answer"}
    assert not card_is_usable(base)
    assert not card_is_usable({**base, "judge": {"verdict": "fail"}})
    assert card_is_usable({**base, "judge": {"verdict": "pass"}})


def test_card_render_attaches_need_to_source_target_relation():
    c = Candidate(
        uid="tgt", doc_id=1, path=("66",), text="Thirty-day procedure.",
        scope=WITHIN, group=1, tokens=3, target_doc="ACT",
        representation="citation_card", source_path=("65", "2"),
        information_need="What procedure applies?", evidence_card_id="card",
    )
    block = render_block(c, "g2e1")
    assert "CITATION_CARD" in block
    assert "SOURCE Article 65.2 -> TARGET ACT Article 66" in block
    assert "What procedure applies?" in block


def test_structured_cache_writes_only_validated_json(tmp_path):
    calls = []

    def backend(messages, temperature, max_tokens):
        calls.append(messages)
        return json.dumps({
            "status": "supported", "evidence": "Thirty days.",
            "support_spans": [
                "The Agency shall assess the application within 30 days."],
        })

    req = fixture_request()
    need = validate_need({
        "need_type": "procedure", "question": "What deadline applies?",
        "required_fields": ["deadline"], "status": "needed",
    })
    llm = StructuredLLM(backend, StructuredCache(tmp_path), "test/model")
    messages = build_extraction_messages(req, need)
    validator = lambda value: validate_extraction(value, req.target_text)
    one, h1 = llm.complete("extract", EXTRACT_PROMPT_VERSION, messages, 200,
                           validator)
    two, h2 = llm.complete("extract", EXTRACT_PROMPT_VERSION, messages, 200,
                           validator)
    assert one == two and h1 == h2
    assert len(calls) == 1


def test_malformed_response_is_not_cached(tmp_path):
    llm = StructuredLLM(lambda *args: "not json", StructuredCache(tmp_path),
                        "test/model")
    with pytest.raises(StructuredResponseError, match="JSON object") as caught:
        llm.complete("need", "v", [], 10, validate_need)
    assert len(caught.value.request_hash) == 64
    assert caught.value.transport == {}
    assert not list(tmp_path.glob("*.json"))


def test_request_options_are_part_of_cache_identity():
    base = dict(model="m", prompt_version="p", stage="judge",
                temperature=1.0, max_tokens=10, messages=[])
    on = llm_payload_hash(**base, request_options={
        "chat_template_kwargs": {"enable_thinking": True}})
    off = llm_payload_hash(**base, request_options={
        "chat_template_kwargs": {"enable_thinking": False}})
    assert on != off


def test_rate_limiter_callback_runs_for_initial_call_and_retry(tmp_path,
                                                               monkeypatch):
    attempts = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"choices": []}'

    def fake_urlopen(request, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise llm_module.urllib.error.URLError("temporary")
        return Response()

    monkeypatch.setattr(llm_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(llm_module.time, "sleep", lambda seconds: None)
    launches = []
    client = LLMClient(tmp_path / "transport", api_key="test-key")
    response = client._post(
        {"model": "m", "messages": []},
        before_request=lambda: launches.append(1))
    assert response == {"choices": []}
    assert len(attempts) == 2
    assert len(launches) == 2, "the retry must not bypass global rate control"


def test_parse_json_object_accepts_one_code_fence():
    assert parse_json_object("```json\n{\"status\": \"needed\"}\n```") == {
        "status": "needed"}


def test_parse_json_object_uses_first_complete_object_not_greedy_regex():
    text = "analysis prefix\n{\"status\": \"supported\"}\nextra {\"x\": 2}"
    assert parse_json_object(text) == {"status": "supported"}
