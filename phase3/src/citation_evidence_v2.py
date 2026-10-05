"""Citation-conditioned evidence cards for Phase 3 hierarchical summaries.

This module deliberately implements a fixed two-stage LLM workflow, not an
agent.  Stage 1 states what a source passage needs from one resolved citation;
Stage 2 answers that need from the resolved target passage only.  Records are
content-addressed and retain exact target support spans for audit.

The gold EUR-Lex summary is never accepted by any public function here.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from llm_provider_v2 import unpack_backend_response


SCHEMA_VERSION = "citation-evidence-v1.0"
NEED_PROMPT_VERSION = "citation-need-v1.3"
EXTRACT_PROMPT_VERSION = "citation-extract-v1.6"
JUDGE_PROMPT_VERSION = "citation-judge-v1.4"

NEED_TYPES = {
    "definition", "scope", "condition", "exception", "obligation",
    "permission", "prohibition", "procedure", "threshold", "dependency",
    "other", "none",
}

_DUTY_RE = re.compile(
    r"\b(?:must|is required to|are required to|shall(?!\s+have\s+the\s+right))\b",
    flags=re.IGNORECASE)
_LEGAL_SENTENCE_RE = re.compile(r"(?<=[.;:])\s+|\n+")
_DECISION_RELABEL_RE = re.compile(
    r"\bdecisions?\b[^.;]{0,240}\b(?:include|includes|comprise|comprises|are)\b"
    r"[^.;]{0,240}\b(?:recommendations?|proposals?|opinions?)\b",
    flags=re.IGNORECASE,
)
_QUOTED_AMENDMENT_RE = re.compile(
    r"^\s*\d+\.\s*(?:in\s+)?Article\s+\d+[a-z]?"
    r"(?:\([^)]{1,3}\))*[^\n]{0,180}\b"
    r"(?:replaced|added|inserted|amended)\b[\s\S]*?[‘’“”\"']",
    flags=re.IGNORECASE,
)

NEED_SYSTEM = """You analyse exactly ONE resolved legal citation. Identify only
what the SOURCE PASSAGE needs from that exact cited TARGET LOCATION to be
understood correctly. The RESOLVED CITATION MENTION is the anchor: do not create
a question about nearby terminology unless the source explicitly connects that
terminology to this citation. If the source contains several citations, ask only
about this one target; never combine other Articles into the question.

Choose one need_type from: definition, scope, condition, exception, obligation,
permission, prohibition, procedure, threshold, dependency, other, none.
Return strict JSON only:
{"need_type":"one value from the list", "question":"one precise question, or empty when none", "required_fields":["actor, condition, threshold or other answer field"], "status":"needed or not_needed"}

Examples of precise dependency questions: "What period is specified in Article
11(5)(c)?"; "What general rule does this notwithstanding clause displace?";
"What objectives are set out in Article 1?". Do not put only an Article number
in required_fields. The phrase "in accordance with Article X" does not by
itself mean that the source needs a step-by-step procedure: ask for the
operative rules, conditions or dependency supplied by that exact target. When
the source explicitly says "the procedure referred to in Article X", ask what
Article X itself specifies; if it is only a wrapper pointing to a further
governing provision, that dependency is a valid answer. Use not_needed when the reference is merely bibliographic,
the cited material is already quoted in the source, or the source is otherwise
self-contained. Do not answer the question, use outside legal knowledge, view
the target text, or use a gold/reference summary."""

EXTRACT_SYSTEM = """You extract citation-conditioned evidence from one legal
TARGET PROVISION. Answer only the supplied INFORMATION NEED and use only the
target text. Preserve relevant actors, conditions, exceptions, numbers, dates,
thresholds and cross-reference dependencies. Search the entire target before
answering; do not stop at the first topically related sentence. Match the legal
category requested: for an obligation prefer applicable shall/must duties over
rights or optional may provisions. "Shall have the right" states a right, not
an obligation; "may" states a permission, not a duty. Preserve formal legal act
types exactly: a recommendation, proposal or opinion is not a decision. If a
need asks for decisions, include only decisions as answers; procedural
recommendations may be mentioned only as recommendations and never grouped as
decisions. For an exception preserve its trigger and
limits; for a procedure preserve its actor, branches, steps, deadlines and
exceptions that are directly relevant to the need. If the cited target only
identifies a further governing provision and the question asks what this target
itself specifies, return that dependency rather than inventing the downstream
procedure. Address every
required field that the target actually supports. Do not summarise unrelated
parts, use outside knowledge, or add conclusions. Return strict JSON only:
{"status":"supported|insufficient_evidence",
 "evidence":"compact answer, or empty when insufficient",
 "support_spans":["short verbatim span copied from TARGET PROVISION"]}
Every substantive claim in evidence must be supported by the listed verbatim
spans. Include a sufficient support span for every separate claim; do not rely
on a span that merely names another Article. Do not repeat a premise from the
question as a factual claim unless the target itself supports it. A compact
answer need not reproduce unrelated parts of the target or every possible
detail. If the target does not answer the exact one-edge need, return
insufficient_evidence."""

JUDGE_SYSTEM = """You are a separate factual-support verification pass. Decide
whether every claim in a proposed CITATION EVIDENCE CARD is supported by the
provided TARGET PROVISION and whether it answers the stated INFORMATION NEED.
Use no outside knowledge. Match legal modality exactly: a right or a `may`
permission does not answer a request for an obligation, and `shall have the
right` is not a mandatory duty. Preserve formal legal act types: fail a card
that groups a recommendation, proposal or opinion as a decision, but do not
fail it merely for mentioning a recommendation when it is explicitly labelled
as a recommendation and explains the decision procedure. Read the question
literally: if it asks for the general rule behind an exception, stating that
general rule answers it. A concise answer need not exhaust the target, repeat
the question's subject, or add unrelated procedure. For a procedural need,
fail an answer that omits a directly relevant branch, deadline or exception
stated in the target. Check that the listed spans
collectively support every card claim, not merely that each span occurs in the
target. Return strict JSON only:
{"verdict":"pass|fail", "supported":true, "answers_need":true,
 "reason":"one short audit reason"}
Pass only when supported and answers_need are both true."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def request_id(source_uid: str, target_uid: str, scope: str) -> str:
    return sha256_json({"source_uid": source_uid, "target_uid": target_uid,
                        "scope": scope})


def parse_json_object(text: str) -> dict:
    """Parse the first complete JSON object, ignoring surrounding model prose.

    NVIDIA-hosted instruction models occasionally emit a valid object followed
    by an explanation even when told to return JSON only.  ``raw_decode`` finds
    the first syntactically complete object without the unsafe greedy-regex
    behaviour that combines two objects into malformed JSON.  Schema and
    grounding validation still run after parsing.
    """
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned,
                     flags=re.IGNORECASE | re.DOTALL).strip()
    decoder = json.JSONDecoder()
    value = None
    for match in re.finditer(r"\{", cleaned):
        try:
            candidate, _ = decoder.raw_decode(cleaned[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict):
            value = candidate
            break
    if value is None:
        raise ValueError("LLM response did not contain a valid JSON object")
    if not isinstance(value, dict):
        raise ValueError("LLM response must be one JSON object")
    return value


def _normalise_ws(text: str) -> str:
    return " ".join((text or "").split())


def _span_is_in_target(span: str, target_text: str) -> bool:
    return bool(span.strip()) and _normalise_ws(span) in _normalise_ws(target_text)


@dataclass(frozen=True)
class CitationRequest:
    request_id: str
    celex: str
    scope: str
    group: int
    source_uid: str
    source_doc: str
    source_path: tuple[str, ...]
    source_text: str
    target_uid: str
    target_doc: str
    target_path: tuple[str, ...]
    target_text: str
    citation_mentions: tuple[str, ...] = ()
    resolution_methods: tuple[str, ...] = ()
    citation_keywords: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, row: dict) -> "CitationRequest":
        required = (
            "request_id", "celex", "scope", "group", "source_uid",
            "source_doc", "source_path", "source_text", "target_uid",
            "target_doc", "target_path", "target_text",
        )
        missing = [key for key in required if key not in row]
        if missing:
            raise ValueError("citation request missing: " + ", ".join(missing))
        expected = request_id(row["source_uid"], row["target_uid"], row["scope"])
        if row["request_id"] != expected:
            raise ValueError("citation request_id does not match its relation")
        return cls(**{**{k: row[k] for k in required},
                      "group": int(row["group"]),
                      "source_path": tuple(row["source_path"]),
                      "target_path": tuple(row["target_path"]),
                      "citation_mentions": tuple(row.get("citation_mentions") or ()),
                      "resolution_methods": tuple(row.get("resolution_methods") or ()),
                      "citation_keywords": tuple(row.get("citation_keywords") or ())})

    def public_record(self) -> dict:
        return {
            "request_id": self.request_id, "celex": self.celex,
            "scope": self.scope, "group": self.group,
            "source_uid": self.source_uid, "source_doc": self.source_doc,
            "source_path": list(self.source_path),
            "target_uid": self.target_uid, "target_doc": self.target_doc,
            "target_path": list(self.target_path),
            "citation_mentions": list(self.citation_mentions),
            "resolution_methods": list(self.resolution_methods),
            "citation_keywords": list(self.citation_keywords),
        }


def deterministic_need(req: CitationRequest) -> dict | None:
    """Return a safe source-only abstention for fully quoted amendments."""
    if _QUOTED_AMENDMENT_RE.search(req.source_text):
        return {
            "need_type": "none", "question": "", "required_fields": [],
            "status": "not_needed",
            "validation_reason": "cited replacement/amendment text is quoted in source",
        }
    return None


def citation_source_context(req: CitationRequest, radius: int = 700) -> str:
    """Return deterministic local windows around this edge's exact mentions."""
    if not req.citation_mentions:
        return req.source_text
    lowered = req.source_text.lower()
    windows = []
    for mention in req.citation_mentions:
        needle = mention.strip()
        if not needle:
            continue
        start = 0
        while True:
            pos = lowered.find(needle.lower(), start)
            if pos < 0:
                break
            lo = max(0, pos - radius)
            hi = min(len(req.source_text), pos + len(needle) + radius)
            window = req.source_text[lo:hi].strip()
            if window and window not in windows:
                windows.append(window)
            start = pos + max(len(needle), 1)
    # A resolver mention should occur verbatim after whitespace cleaning. If a
    # legacy or unusual record violates that expectation, preserve correctness
    # by falling back to the complete source rather than inventing context.
    return "\n\n[... another matching citation window ...]\n\n".join(windows) \
        if windows else req.source_text


def build_need_messages(req: CitationRequest) -> list[dict]:
    mentions = ("\n- ".join(req.citation_mentions)
                if req.citation_mentions else "(legacy graph: mention unavailable)")
    user = (
        f"SOURCE LOCATION: {req.source_doc} / {'.'.join(req.source_path)}\n"
        f"RESOLVED TARGET: {req.target_doc} / {'.'.join(req.target_path)}\n\n"
        f"RESOLVED CITATION MENTION(S):\n- {mentions}\n\n"
        f"CITATION-LOCAL SOURCE CONTEXT:\n{citation_source_context(req)}\n\n"
        "State the information need created by this resolved citation."
    )
    return [{"role": "system", "content": NEED_SYSTEM},
            {"role": "user", "content": user}]


def validate_need(value: dict) -> dict:
    need_type = str(value.get("need_type", "")).strip().lower()
    status = str(value.get("status", "")).strip().lower()
    question = _normalise_ws(str(value.get("question", "")))
    fields = value.get("required_fields", [])
    if need_type not in NEED_TYPES:
        parts = [x.strip() for x in re.split(r"[|/,]", need_type) if x.strip()]
        if not parts or any(x not in NEED_TYPES - {"none"} for x in parts):
            raise ValueError(f"invalid need_type: {need_type!r}")
        # The question remains the binding specification. Choosing the first
        # valid label preserves modality gates without dropping the request.
        need_type = parts[0]
    if status not in {"needed", "not_needed"}:
        raise ValueError(f"invalid need status: {status!r}")
    if not isinstance(fields, list) or not all(isinstance(x, str) for x in fields):
        raise ValueError("required_fields must be a list of strings")
    fields = [_normalise_ws(x) for x in fields if _normalise_ws(x)]
    if status == "needed" and not question:
        raise ValueError("a needed citation must contain a question")
    if status == "not_needed":
        need_type, question, fields = "none", "", []
    elif need_type == "obligation" and "exclude rights" not in question.lower():
        question += (" Identify mandatory duties only; exclude rights and "
                     "optional 'may' permissions.")
    elif ("decision" in question.lower()
          and "distinguish decisions" not in question.lower()):
        question += (" Distinguish decisions from recommendations, proposals "
                     "and opinions; do not group those acts as decisions.")
    return {"need_type": need_type, "question": question,
            "required_fields": fields, "status": status}


def build_extraction_messages(req: CitationRequest, need: dict) -> list[dict]:
    need = validate_need(need)
    locators = []
    if need["need_type"] == "obligation":
        duty_candidates = [
            _normalise_ws(sentence) for sentence in
            _LEGAL_SENTENCE_RE.split(req.target_text)
            if _DUTY_RE.search(sentence)
        ]
        if duty_candidates:
            locators.append(
                "\n\nMANDATORY-DUTY LOCATOR (sentences selected "
                "deterministically from the same target; verify them against "
                "the full text):\n- " + "\n- ".join(duty_candidates)
            )
    if "decision" in need["question"].lower():
        decision_candidates = [
            _normalise_ws(sentence) for sentence in
            _LEGAL_SENTENCE_RE.split(req.target_text)
            if re.search(r"\b(?:decisions?|decides?|adopt(?:s|ed|ion)?)\b",
                         sentence, flags=re.IGNORECASE)
        ]
        if decision_candidates:
            locators.append(
                "\n\nDECISION LOCATOR (sentences selected deterministically "
                "from the same target; verify them against the full text and "
                "distinguish decisions from recommendations, proposals and "
                "opinions):\n- " + "\n- ".join(decision_candidates)
            )
    locator = "".join(locators)
    user = (
        f"INFORMATION NEED:\n{_canonical_json(need)}\n\n"
        f"TARGET LOCATION: {req.target_doc} / {'.'.join(req.target_path)}\n\n"
        f"TARGET PROVISION:\n{req.target_text}{locator}\n\n"
        "Extract only the target information required by the information need."
    )
    return [{"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": user}]


def validate_extraction(value: dict, target_text: str) -> dict:
    status = str(value.get("status", "")).strip().lower()
    model_evidence = _normalise_ws(str(
        value.get("model_evidence", value.get("evidence", ""))))
    spans = value.get("support_spans", [])
    if status not in {"supported", "insufficient_evidence"}:
        raise ValueError(f"invalid extraction status: {status!r}")
    if not isinstance(spans, list) or not all(isinstance(x, str) for x in spans):
        raise ValueError("support_spans must be a list of strings")
    spans = [_normalise_ws(x) for x in spans if _normalise_ws(x)]
    if status == "supported":
        if not model_evidence:
            raise ValueError("supported extraction has empty evidence")
        if not spans:
            raise ValueError("supported extraction has no support spans")
        absent = [span for span in spans if not _span_is_in_target(span, target_text)]
        if absent:
            raise ValueError("support span is not verbatim in target text")
        # Only the model-selected verbatim text is admitted to the downstream
        # summary context. The model paraphrase is retained solely for audit.
        spans = list(dict.fromkeys(spans))
        evidence = " ".join(spans)
    else:
        evidence, spans = "", []
    out = {"status": status, "evidence": evidence, "support_spans": spans}
    if status == "supported":
        out["model_evidence"] = model_evidence
    return out


def validate_extraction_for_need(value: dict, target_text: str,
                                 need: dict) -> dict:
    """Grounding plus a conservative legal-modality sanity gate.

    The judge remains necessary, but it cannot turn a permission into a duty.
    If an obligation card contains no duty marker after excluding the common
    phrase ``shall have the right``, the safe result is an audited abstention.
    """
    try:
        out = validate_extraction(value, target_text)
    except ValueError as exc:
        # Grounding failures are audited abstentions, not reasons to stop a
        # multi-hour resumable run or to admit an unsupported paraphrase.
        if "support span is not verbatim" not in str(exc):
            raise
        return {
            "status": "insufficient_evidence", "evidence": "",
            "support_spans": [],
            "validation_reason": "support span was not verbatim in target",
        }
    need = validate_need(need)
    audit_evidence = out.get("model_evidence", out["evidence"])
    if (out["status"] == "supported" and need["need_type"] == "obligation"
            and not _DUTY_RE.search(audit_evidence)):
        return {
            "status": "insufficient_evidence", "evidence": "",
            "support_spans": [],
            "validation_reason": "obligation need lacked a mandatory duty",
        }
    if (out["status"] == "supported"
            and "decision" in need["question"].lower()
            and _DECISION_RELABEL_RE.search(audit_evidence)):
        return {
            "status": "insufficient_evidence", "evidence": "",
            "support_spans": [],
            "validation_reason": (
                "recommendation/proposal/opinion was grouped as a decision"),
        }
    return out


def build_judge_messages(req: CitationRequest, need: dict,
                         extraction: dict) -> list[dict]:
    proposed = validate_extraction(extraction, req.target_text)
    proposed.pop("model_evidence", None)
    user = (
        f"INFORMATION NEED:\n{_canonical_json(validate_need(need))}\n\n"
        f"PROPOSED EVIDENCE CARD:\n"
        f"{_canonical_json(proposed)}\n\n"
        f"TARGET PROVISION:\n{req.target_text}\n\nVerify the proposed card."
    )
    return [{"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user}]


def validate_judgement(value: dict) -> dict:
    verdict = str(value.get("verdict", "")).strip().lower()
    supported = value.get("supported")
    answers_need = value.get("answers_need")
    reason = _normalise_ws(str(value.get("reason", "")))
    if verdict not in {"pass", "fail"}:
        raise ValueError(f"invalid judge verdict: {verdict!r}")
    if not isinstance(supported, bool) or not isinstance(answers_need, bool):
        raise ValueError("judge supported/answers_need must be booleans")
    if (verdict == "pass") != (supported and answers_need):
        raise ValueError("judge verdict conflicts with its boolean fields")
    return {"verdict": verdict, "supported": supported,
            "answers_need": answers_need, "reason": reason}


def llm_payload_hash(model: str, prompt_version: str, stage: str,
                     temperature: float, max_tokens: int,
                     messages: Sequence[dict],
                     request_options: dict | None = None) -> str:
    return sha256_json({
        "model": model, "prompt_version": prompt_version, "stage": stage,
        "temperature": temperature, "max_tokens": max_tokens,
        "request_options": request_options or {},
        "messages": [{"role": m["role"], "content": m["content"]}
                     for m in messages],
    })


class StructuredCache:
    """Cache only validated structured responses, keyed by the full payload."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.writes = 0
        self._lock = threading.Lock()

    def path_for(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict | None:
        row = self.get_entry(key)
        return None if row is None else row["value"]

    def get_entry(self, key: str, count_hit: bool = True) -> dict | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        row = json.loads(path.read_text())
        if row.get("request_hash") != key or not isinstance(row.get("value"), dict):
            raise ValueError(f"invalid structured cache entry: {path.name}")
        if count_hit:
            with self._lock:
                self.hits += 1
        return row

    def put(self, key: str, value: dict, metadata: dict) -> None:
        self.path_for(key).write_text(json.dumps({
            "request_hash": key, "value": value, **metadata,
        }, ensure_ascii=False))
        with self._lock:
            self.writes += 1


class StructuredLLM:
    """Validated, content-addressed LLM wrapper for the fixed card stages."""

    def __init__(self, backend: Callable, cache: StructuredCache, model: str,
                 dry_run: bool = False,
                 request_options: dict | None = None):
        self.backend = backend
        self.cache = cache
        self.model = model
        self.dry_run = dry_run
        self.request_options = request_options or {}
        self.calls = 0
        self._lock = threading.Lock()

    def complete(self, stage: str, prompt_version: str,
                 messages: Sequence[dict], max_tokens: int,
                 validator: Callable[[dict], dict],
                 temperature: float = 0.0) -> tuple[dict | None, str]:
        key = llm_payload_hash(self.model, prompt_version, stage, temperature,
                               max_tokens, messages, self.request_options)
        hit = self.cache.get(key)
        if hit is not None:
            return validator(hit), key
        if self.dry_run:
            return None, key
        raw, transport = unpack_backend_response(
            self.backend(messages, temperature, max_tokens))
        try:
            value = validator(parse_json_object(raw))
        except (TypeError, ValueError) as exc:
            raise StructuredResponseError(
                str(exc), request_hash=key, transport=transport) from exc
        with self._lock:
            self.calls += 1
        self.cache.put(key, value, {
            "model": self.model, "prompt_version": prompt_version,
            "stage": stage, "temperature": temperature,
            "max_tokens": max_tokens,
            "request_options": self.request_options,
            "transport": transport,
        })
        return value, key

    def transport_for(self, key: str | None) -> dict | None:
        if key is None:
            return None
        row = self.cache.get_entry(key, count_hit=False)
        return None if row is None else row.get("transport", {})


class StructuredResponseError(ValueError):
    """A provider response arrived but failed JSON/schema/grounding validation."""

    def __init__(self, message: str, request_hash: str, transport: dict):
        super().__init__(message)
        self.request_hash = request_hash
        self.transport = dict(transport)


def card_is_usable(card: dict, require_judge: bool = True) -> bool:
    if card.get("status") != "supported" or not card.get("evidence"):
        return False
    if require_judge:
        judge = card.get("judge") or {}
        return judge.get("verdict") == "pass"
    return True
