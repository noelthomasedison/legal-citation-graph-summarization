"""Build verified citation-conditioned evidence cards (fixed workflow).

This is deliberately not an agent.  For every frozen source-target request:
  1. Llama identifies the information the source needs from that target.
  2. Llama extracts only that information from the target provision.
  3. A separate frozen Llama prompt verifies support and relevance.

All validated stage responses are content-addressed.  The JSONL output is
append-only/resumable, and a manifest binds it to the request artefact.  Gold
summaries are never loaded.
"""
import argparse
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from citation_evidence_v2 import (                         # noqa: E402
    EXTRACT_PROMPT_VERSION, JUDGE_PROMPT_VERSION, NEED_PROMPT_VERSION,
    SCHEMA_VERSION, CitationRequest, StructuredCache, StructuredLLM,
    StructuredResponseError,
    build_extraction_messages, build_judge_messages, build_need_messages,
    card_is_usable, deterministic_need, sha256_json, validate_judgement,
    validate_extraction_for_need, validate_need,
)
from context_v2 import sha256_file                         # noqa: E402
from llm_provider_v2 import (                              # noqa: E402
    BackendResponse, load_api_key, resolve_inference_config,
    response_metadata,
)
from regkg.llm_extract import LLMClient                    # noqa: E402


ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--artifact-tag", required=True,
                help="tag used by script 13 when exporting requests")
ap.add_argument("--requests", type=Path,
                help="override the tagged request JSONL path")
ap.add_argument("--act-list", type=Path,
                help="optional JSON/text CELEX list; process only these acts")
ap.add_argument("--limit", type=int, default=0,
                help="smoke-test only: process the first N selected requests")
ap.add_argument("--workers", type=int, default=1,
                help="sequential by default, matching the stable Phase 2 runs")
ap.add_argument("--rpm", type=float, default=20.0,
                help="global launch rate across initial calls and retries")
ap.add_argument("--provider", choices=("nvidia", "openrouter"), default="nvidia")
ap.add_argument("--model", default=None,
                help="provider model id; defaults to Llama 3.3 70B for that provider")
ap.add_argument("--judge-model", default=None,
                help="defaults to the same provider/model as extraction")
ap.add_argument("--endpoint-provider", default="coreweave",
                help="pinned OpenRouter provider slug")
ap.add_argument("--quantization", default="fp16",
                help="pinned OpenRouter quantization (default: fp16)")
ap.add_argument("--allow-provider-fallbacks", action="store_true",
                help="allow OpenRouter to change serving provider (off for research runs)")
ap.add_argument("--need-max-tokens", type=int, default=192)
ap.add_argument("--extract-max-tokens", type=int, default=320)
ap.add_argument("--judge-max-tokens", type=int, default=160)
ap.add_argument("--temperature", type=float, default=0.0)
ap.add_argument("--judge-temperature", type=float, default=0.0)
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

if not args.artifact_tag.replace("_", "").isalnum():
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
if not 1 <= args.workers <= 8:
    sys.exit("--workers must be between 1 and 8")
if not 1 <= args.rpm <= 120:
    sys.exit("--rpm must be between 1 and 120")
try:
    extractor_inference = resolve_inference_config(
        args.provider, args.model, args.endpoint_provider, args.quantization,
        args.allow_provider_fallbacks)
    judge_inference = resolve_inference_config(
        args.provider, args.judge_model or extractor_inference.model,
        args.endpoint_provider, args.quantization,
        args.allow_provider_fallbacks)
except ValueError as exc:
    sys.exit(str(exc))
args.model = extractor_inference.model
args.judge_model = judge_inference.model

REQUESTS = (args.requests or ROOT / "data" /
            f"citation_evidence_requests_hier_v2_{args.split}_{args.artifact_tag}.jsonl")
OUT = ROOT / "data" / f"citation_evidence_cards_hier_v2_{args.split}_{args.artifact_tag}.jsonl"
MANIFEST = OUT.with_name(OUT.stem + "_manifest.json")
CACHE = ROOT / "data" / "citation_evidence_v2_cache"

if not REQUESTS.exists():
    sys.exit(f"request artefact missing: {REQUESTS}")


def load_act_list(path):
    if path is None:
        return None
    raw = path.read_text().strip()
    try:
        value = json.loads(raw)
        acts = value if isinstance(value, list) else value.get("celex_ids", [])
    except json.JSONDecodeError:
        acts = [x.strip() for x in raw.splitlines()
                if x.strip() and not x.lstrip().startswith("#")]
    if not acts or not all(isinstance(x, str) and x for x in acts):
        sys.exit("act list must contain CELEX strings")
    return set(acts)


allowed_acts = load_act_list(args.act_list)
requests = []
seen_requests = set()
for lineno, line in enumerate(REQUESTS.read_text().splitlines(), 1):
    if not line.strip():
        continue
    row = json.loads(line)
    req = CitationRequest.from_dict(row)
    if req.request_id in seen_requests:
        sys.exit(f"duplicate request_id at line {lineno}")
    seen_requests.add(req.request_id)
    if allowed_acts is None or req.celex in allowed_acts:
        requests.append(req)
if not requests:
    sys.exit("no citation requests selected")
if args.limit < 0:
    sys.exit("--limit cannot be negative")
if args.limit:
    requests = requests[:args.limit]

# Resume only records that exactly match the frozen relation.  The content
# hashes in each stage protect against source/target or prompt changes.
done = {}
expected_models = {"need_and_extraction": args.model,
                   "support_judge": args.judge_model}
expected_inference = {
    "need_and_extraction": extractor_inference.public_record(),
    "support_judge": judge_inference.public_record(),
}
judge_is_nemotron = "nemotron-3" in args.judge_model.lower()
judge_model_options = (
    {"top_p": 0.95, "chat_template_kwargs": {"enable_thinking": False}}
    if judge_is_nemotron else {})
json_options = ({"response_format": {"type": "json_object"}}
                if args.provider == "openrouter" else {})
extractor_request_options = {
    **extractor_inference.request_options(), **json_options,
}
judge_request_options = {
    **judge_inference.request_options(), **json_options, **judge_model_options,
}
expected_request_options = {
    "need_and_extraction": extractor_request_options,
    "support_judge": judge_request_options,
}
expected_prompt_versions = {
    "need": NEED_PROMPT_VERSION, "extraction": EXTRACT_PROMPT_VERSION,
    "judge": JUDGE_PROMPT_VERSION,
}
expected_settings = {
    "temperature": args.temperature,
    "judge_temperature": args.judge_temperature,
    "judge_top_p": 0.95 if judge_is_nemotron else None,
    "judge_enable_thinking": False if judge_is_nemotron else None,
    "need_max_tokens": args.need_max_tokens,
    "extract_max_tokens": args.extract_max_tokens,
    "judge_max_tokens": args.judge_max_tokens,
}
if OUT.exists():
    for lineno, line in enumerate(OUT.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        rid = row.get("request_id")
        if not rid or rid in done:
            sys.exit(f"invalid/duplicate completed card at line {lineno}")
        done[rid] = row
selected_ids = {req.request_id for req in requests}
extra_done = sorted(set(done) - selected_ids)
if extra_done:
    sys.exit("existing output contains records outside the current selection; "
             "use a new --artifact-tag rather than truncating it")


class LaunchRateLimiter:
    """Globally space starts; provider backoff still handles 429/503 responses."""

    def __init__(self, rpm):
        self.interval = 60.0 / rpm
        self.next_start = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next_start - now)
            if delay:
                time.sleep(delay)
            self.next_start = time.monotonic() + self.interval


launch_limiter = LaunchRateLimiter(args.rpm)


def backend_for(inference, extra_payload=None):
    phase1_root = ROOT.parent / "phase1"
    key, key_source = load_api_key(inference, phase1_root)
    if not key:
        expected = ("OPENROUTER_API_KEY or phase1/.openrouter_api_key"
                    if inference.gateway == "openrouter"
                    else "NVIDIA_API_KEY or phase1/.nvidia_api_key")
        sys.exit(f"no {inference.gateway} API key; set {expected}")
    client = LLMClient(
        cache_dir=CACHE / "transport", model=inference.model,
        base_url=inference.base_url, api_key=key)

    def backend(messages, temperature, max_tokens):
        payload = {"model": inference.model, "temperature": temperature,
                   "max_tokens": max_tokens, "messages": list(messages)}
        payload.update(inference.request_options())
        payload.update(extra_payload or {})
        response = client._post(payload, before_request=launch_limiter.wait)
        metadata = response_metadata(response, inference)
        metadata["key_source"] = key_source
        return BackendResponse(
            response["choices"][0]["message"]["content"].strip(), metadata)
    return backend


if args.dry_run:
    extractor_backend = judge_backend = lambda *a, **k: ""
else:
    extractor_backend = backend_for(extractor_inference, json_options)
    judge_backend = backend_for(
        judge_inference, {**json_options, **judge_model_options})

extractor = StructuredLLM(
    extractor_backend, StructuredCache(CACHE / "extractor"), args.model,
    dry_run=args.dry_run, request_options=extractor_request_options)
judge = StructuredLLM(
    judge_backend, StructuredCache(CACHE / "judge"), args.judge_model,
    dry_run=args.dry_run,
    request_options=judge_request_options)

new_rows = 0
planned = {"need": 0, "extract": 0, "judge": 0}
status_counts = {}
t0 = time.time()


def request_content(req):
    return {
        "source_text": req.source_text,
        "target_text": req.target_text,
        "citation_mentions": list(req.citation_mentions),
        "resolution_methods": list(req.resolution_methods),
        "citation_keywords": list(req.citation_keywords),
    }


def validate_resume(req, previous):
    if (previous.get("source_uid") != req.source_uid
            or previous.get("target_uid") != req.target_uid
            or previous.get("scope") != req.scope
            or previous.get("request_content_sha256") !=
            sha256_json(request_content(req))):
        raise ValueError(f"resume mismatch for request {req.request_id}")
    if (previous.get("models") != expected_models
            or previous.get("inference") != expected_inference
            or previous.get("request_options") != expected_request_options
            or previous.get("prompt_versions") != expected_prompt_versions
            or previous.get("settings") != expected_settings):
        raise ValueError(
            f"resume configuration mismatch for {req.request_id}; use a new "
            "--artifact-tag rather than mixing card versions")


def process_one(req):
    """One fixed relation pipeline; relations may run concurrently."""
    stage_errors = {}
    need = deterministic_need(req)
    if need is not None:
        need_hash = sha256_json({
            "stage": "deterministic_need", "version": NEED_PROMPT_VERSION,
            "request": request_content(req), "result": need,
        })
        need_transport = None
    else:
        need_messages = build_need_messages(req)
        try:
            need, need_hash = extractor.complete(
                "need", NEED_PROMPT_VERSION, need_messages, args.need_max_tokens,
                validate_need, temperature=args.temperature)
            need_transport = extractor.transport_for(need_hash)
        except StructuredResponseError as exc:
            need_hash, need_transport = exc.request_hash, exc.transport
            stage_errors["need"] = str(exc)[:240]
            need = {"need_type": "none", "question": "", "required_fields": [],
                    "status": "not_needed",
                    "validation_reason": "invalid structured need response"}
    extraction = {"status": "insufficient_evidence", "evidence": "",
                  "support_spans": []}
    extraction_hash = None
    extraction_transport = None
    judgement = None
    judgement_hash = None
    judge_transport = None
    status = "need_validation_error" if stage_errors else "not_needed"
    if not stage_errors and need["status"] == "needed":
        extraction_messages = build_extraction_messages(req, need)
        try:
            extraction, extraction_hash = extractor.complete(
                "extract", EXTRACT_PROMPT_VERSION, extraction_messages,
                args.extract_max_tokens,
                lambda value: validate_extraction_for_need(
                    value, req.target_text, need),
                temperature=args.temperature)
            extraction_transport = extractor.transport_for(extraction_hash)
        except StructuredResponseError as exc:
            extraction_hash, extraction_transport = exc.request_hash, exc.transport
            stage_errors["extraction"] = str(exc)[:240]
            extraction = {
                "status": "insufficient_evidence", "evidence": "",
                "support_spans": [],
                "validation_reason": "invalid structured extraction response",
            }
        status = extraction["status"]
        if status == "supported":
            judge_messages = build_judge_messages(req, need, extraction)
            try:
                judgement, judgement_hash = judge.complete(
                    "judge", JUDGE_PROMPT_VERSION, judge_messages,
                    args.judge_max_tokens, validate_judgement,
                    temperature=args.judge_temperature)
                judge_transport = judge.transport_for(judgement_hash)
            except StructuredResponseError as exc:
                judgement_hash, judge_transport = exc.request_hash, exc.transport
                stage_errors["judge"] = str(exc)[:240]
                status = "judge_validation_error"
            if judgement is not None and judgement["verdict"] != "pass":
                status = "rejected_by_judge"
    record = {
        "schema_version": SCHEMA_VERSION, **req.public_record(),
        "request_content_sha256": sha256_json(request_content(req)),
        "status": status, "need": need,
        "evidence": extraction["evidence"] if status == "supported" else "",
        "support_spans": (extraction["support_spans"]
                          if status == "supported" else []),
        "extraction": extraction, "judge": judgement,
        "hashes": {"need": need_hash, "extraction": extraction_hash,
                   "judge": judgement_hash},
        "transport": {
            "need": need_transport,
            "extraction": extraction_transport,
            "judge": judge_transport,
        },
        "stage_errors": stage_errors,
        "models": expected_models, "inference": expected_inference,
        "request_options": expected_request_options,
        "prompt_versions": expected_prompt_versions,
        "settings": expected_settings,
    }
    if status == "supported" and not card_is_usable(record, True):
        raise AssertionError("supported card did not pass usability gate")
    return record


todo = []
for req in requests:
    previous = done.get(req.request_id)
    if previous is not None:
        try:
            validate_resume(req, previous)
        except ValueError as exc:
            sys.exit(str(exc))
        status = previous.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    else:
        todo.append(req)

if args.dry_run:
    planned = {"need": len(todo), "extract": len(todo), "judge": len(todo)}
else:
    out_f = open(OUT, "a")
    try:
        completed_total = len(requests) - len(todo)

        def write_record(req, record):
            global new_rows, completed_total
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()
            done[req.request_id] = record
            new_rows += 1
            status = record["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            completed_total += 1
            if completed_total % 10 == 0 or completed_total == len(requests):
                print(f"  {completed_total}/{len(requests)} requests | "
                      f"{extractor.calls + judge.calls} new calls",
                      flush=True)

        if args.workers == 1:
            # Do not pre-submit the whole run. Each card is durably appended
            # before the next request can launch, so a writer error cannot leave
            # queued API calls draining invisibly in ThreadPoolExecutor.shutdown.
            for req in todo:
                write_record(req, process_one(req))
        else:
            pool = ThreadPoolExecutor(max_workers=args.workers)
            futures = {pool.submit(process_one, req): req for req in todo}
            try:
                for future in as_completed(futures):
                    req = futures[future]
                    write_record(req, future.result())
            except BaseException:
                for future in futures:
                    future.cancel()
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            else:
                pool.shutdown(wait=True)
    finally:
        out_f.close()

    # A successful run has a deterministic file order and therefore a stable
    # hash even though relations completed concurrently.
    ordered = [done[req.request_id] for req in sorted(
        requests, key=lambda item: item.request_id)]
    OUT.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n"
                           for row in ordered))

if args.dry_run:
    print(f"requests: {len(requests)} | existing: "
          f"{sum(r.request_id in done for r in requests)}")
    print("conservative planned calls (before cache/abstentions): "
          f"{sum(planned.values())} = {planned}")
    print("DRY RUN — zero API calls and no card rows written")
    sys.exit(0)

try:
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(ROOT.parent),
        stderr=subprocess.DEVNULL).decode().strip()
except Exception:                                           # noqa: BLE001
    commit = "unavailable"

manifest = {
    "schema_version": SCHEMA_VERSION,
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "git_commit": commit,
    "split": args.split, "artifact_tag": args.artifact_tag,
    "requests_artifact": str(REQUESTS),
    "requests_sha256": sha256_file(REQUESTS),
    "cards_artifact": str(OUT.relative_to(ROOT)),
    "cards_sha256": sha256_file(OUT),
    "n_selected_requests": len(requests),
    "selected_request_ids_sha256": sha256_json(
        sorted(req.request_id for req in requests)),
    "n_completed_records": sum(req.request_id in done for req in requests),
    "status_counts": status_counts,
    "usable_supported_cards": sum(
        card_is_usable(done.get(req.request_id, {}), True) for req in requests),
    "models": expected_models,
    "inference": expected_inference,
    "request_options": expected_request_options,
    "prompt_versions": expected_prompt_versions,
    "settings": expected_settings,
    "new_rows": new_rows,
    "workers": args.workers,
    "launch_rpm": args.rpm,
    "new_calls": {"extractor": extractor.calls, "judge": judge.calls},
    "cache_hits": {"extractor": extractor.cache.hits,
                   "judge": judge.cache.hits},
    "elapsed_s": round(time.time() - t0, 1),
    "gold_summary_loaded": False,
}
MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({k: manifest[k] for k in (
    "n_selected_requests", "n_completed_records", "status_counts",
    "usable_supported_cards", "new_calls", "elapsed_s")}, indent=2))
print(f"cards -> {OUT.relative_to(ROOT)}")
print(f"manifest -> {MANIFEST.relative_to(ROOT)}")
