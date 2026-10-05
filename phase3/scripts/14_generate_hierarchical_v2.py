"""Phase 3 v2 — one-level hierarchical generation for all four conditions.

    selected evidence  ->  one brief per non-empty group  ->  one final summary

Every condition uses the SAME architecture; only the evidence differs. The
cache is content-addressed on the full request payload, so identical Stage-1
prompts arising in different conditions cost one call, and any prompt/model/
token change invalidates the entry (v1 keyed on celex+condition and did
neither).

Requires 13_build_contexts_v2.py to have passed. --dry-run makes zero API
calls and simply reports what WOULD be requested.

Writes summaries_hier_v2_<split>.jsonl and run_manifest_hier_v2_<split>.json;
cache lives in data/hier_v2_cache/ (never the v1 sum_cache namespace).
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

from context_v2 import (                                    # noqa: E402
    HierCache, HierLLM, PROMPT_VERSION, STAGE1_SYS, STAGE2_SYS,
    build_stage1_messages, build_stage2_messages, generate_hierarchical,
    generation_settings_hash, payload_hash, sha256_file,
    validate_generation_metadata,
)
from llm_provider_v2 import (                               # noqa: E402
    BackendResponse, load_api_key, resolve_inference_config,
    response_metadata,
)

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
pick = ap.add_mutually_exclusive_group()
pick.add_argument("--n", type=int, default=0,
                  help="0 = all acts; otherwise first N (use --act-list for QA)")
pick.add_argument("--act-list", type=Path,
                  help="JSON list or one CELEX id per line; preserves file order")
ap.add_argument("--conditions", default="base,A,B,oracle")
ap.add_argument("--stage1-max-tokens", type=int, default=256)
ap.add_argument("--final-max-tokens", type=int, default=1024)
ap.add_argument("--temperature", type=float, default=0.0)
ap.add_argument("--provider", choices=("nvidia", "openrouter"), default="nvidia")
ap.add_argument("--model", default=None,
                help="provider model id; defaults to Llama 3.3 70B")
ap.add_argument("--endpoint-provider", default="coreweave",
                help="pinned OpenRouter provider slug")
ap.add_argument("--quantization", default="fp16")
ap.add_argument("--allow-provider-fallbacks", action="store_true",
                help="off by default so the serving backend cannot change")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--artifact-tag", default="",
                help="context/output suffix created by script 13")
ap.add_argument("--workers", type=int, default=1,
                help="sequential by default, matching stable Phase 2 generation")
ap.add_argument("--rpm", type=float, default=20.0,
                help="globally spaced launches with headroom under the 40 RPM limit")
args = ap.parse_args()

SPLIT = args.split
if args.artifact_tag and not args.artifact_tag.replace("_", "").isalnum():
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
if not 1 <= args.workers <= 8:
    sys.exit("--workers must be between 1 and 8")
if not 1 <= args.rpm <= 120:
    sys.exit("--rpm must be between 1 and 120")
try:
    inference = resolve_inference_config(
        args.provider, args.model, args.endpoint_provider, args.quantization,
        args.allow_provider_fallbacks)
except ValueError as exc:
    sys.exit(str(exc))
args.model = inference.model
request_options = inference.request_options()
tag_suffix = f"_{args.artifact_tag}" if args.artifact_tag else ""
CTX_FP = ROOT / "data" / f"contexts_hier_v2_{SPLIT}{tag_suffix}.json"
OUT_FP = ROOT / "data" / f"summaries_hier_v2_{SPLIT}{tag_suffix}.jsonl"
MAN_FP = ROOT / "data" / f"run_manifest_hier_v2_{SPLIT}{tag_suffix}.json"
CTX_MAN_FP = ROOT / "data" / f"context_manifest_hier_v2_{SPLIT}{tag_suffix}.json"
CACHE_DIR = ROOT / "data" / "hier_v2_cache"

if not CTX_FP.exists():
    sys.exit("run 13_build_contexts_v2.py first")
artifact = json.load(open(CTX_FP))
if artifact.get("schema_version") != "hier-v2.1" or "metadata" not in artifact:
    sys.exit("context artefact lacks the Phase 3 v2.1 safety metadata; refusing "
             "generation. Rebuild it with the exact tokenizer.")
metadata = artifact["metadata"]
if metadata.get("evidence_representation") != "citation_card":
    sys.exit(
        "generation blocked: this context uses raw citation targets. The "
        "pre-generation amendment requires verified citation evidence cards.")
try:
    validate_generation_metadata(metadata)
except ValueError as e:
    sys.exit(f"generation blocked: {e}")
if not metadata.get("valid_for_generation", False):
    blockers = metadata.get("budget_validation", {}).get("problems", [])
    sys.exit("generation blocked: context audit did not pass all gates"
             + (" — " + "; ".join(blockers) if blockers else ""))
if not CTX_MAN_FP.exists():
    sys.exit(f"generation blocked: {CTX_MAN_FP.name} is missing")
ctx_manifest = json.load(open(CTX_MAN_FP))
actual_ctx_hash = sha256_file(CTX_FP)
if ctx_manifest.get("context_sha256") != actual_ctx_hash:
    sys.exit("generation blocked: context file hash does not match its manifest")
graph_rel = metadata.get("graph_artifact")
if not graph_rel:
    sys.exit("generation blocked: context metadata does not identify its graph")
graph_fp = ROOT / graph_rel
if (not graph_fp.exists()
        or sha256_file(graph_fp) != metadata.get("graph_sha256")
        or ctx_manifest.get("graph_sha256") != metadata.get("graph_sha256")):
    sys.exit("generation blocked: audited graph file/hash does not match the "
             "context metadata and manifest")
card_meta = metadata.get("citation_evidence", {})
card_artifact = card_meta.get("cards_artifact")
if not card_artifact or not card_meta.get("cards_sha256"):
    sys.exit("generation blocked: citation-card provenance is incomplete")
cards_fp = Path(card_artifact)
if not cards_fp.is_absolute():
    cards_fp = ROOT / cards_fp
if not cards_fp.exists() or sha256_file(cards_fp) != card_meta["cards_sha256"]:
    sys.exit("generation blocked: citation evidence file/hash does not match "
             "the audited context metadata")
embedded_card_manifest = card_meta.get("cards_manifest") or {}
if embedded_card_manifest.get("cards_sha256") != card_meta["cards_sha256"]:
    sys.exit("generation blocked: embedded citation-card manifest mismatch")
contexts = artifact["contexts"]
if args.act_list:
    if not args.act_list.exists():
        sys.exit(f"act list not found: {args.act_list}")
    raw = args.act_list.read_text().strip()
    try:
        loaded = json.loads(raw)
        acts = loaded if isinstance(loaded, list) else loaded.get("celex_ids", [])
    except json.JSONDecodeError:
        acts = [x.strip() for x in raw.splitlines()
                if x.strip() and not x.lstrip().startswith("#")]
    if not acts or not all(isinstance(x, str) and x for x in acts):
        sys.exit("act list must contain CELEX strings")
    if len(acts) != len(set(acts)):
        sys.exit("act list contains duplicate CELEX ids")
    missing = [x for x in acts if x not in contexts]
    if missing:
        sys.exit(f"act list contains ids absent from contexts: {missing[:10]}")
else:
    acts = sorted(contexts)[: args.n] if args.n else sorted(contexts)
CONDS = [c.strip() for c in args.conditions.split(",") if c.strip()]
unknown_conditions = [c for c in CONDS if c not in ("base", "A", "B", "oracle")]
if unknown_conditions:
    sys.exit(f"unknown conditions: {unknown_conditions}")
settings_hash = generation_settings_hash(
    args.model, PROMPT_VERSION, args.temperature,
    args.stage1_max_tokens, args.final_max_tokens, request_options)
print(f"acts: {len(acts)} | conditions: {CONDS} | dry-run: {args.dry_run}")

# ---- resume safety: a completed row is reusable ONLY if its hashes match ----
done = {}
if OUT_FP.exists():
    for line in open(OUT_FP):
        r = json.loads(line)
        key = (r["celex"], r["cond"])
        if key in done:
            sys.exit(f"duplicate completed row in {OUT_FP.name}: {key}")
        done[key] = r
    print(f"resuming: {len(done)} rows already present")

# ---- backend ----
class LaunchRateLimiter:
    def __init__(self, rpm):
        self.interval = 60.0 / rpm
        self.next_start = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            delay = max(0.0, self.next_start - time.monotonic())
            if delay:
                time.sleep(delay)
            self.next_start = time.monotonic() + self.interval


launch_limiter = LaunchRateLimiter(args.rpm)


def make_backend():
    from regkg.llm_extract import LLMClient
    key, key_source = load_api_key(inference, ROOT.parent / "phase1")
    if not key:
        expected = ("OPENROUTER_API_KEY or phase1/.openrouter_api_key"
                    if inference.gateway == "openrouter"
                    else "NVIDIA_API_KEY or phase1/.nvidia_api_key")
        sys.exit(f"no {inference.gateway} API key; set {expected}")
    base = LLMClient(
        cache_dir=CACHE_DIR, model=args.model, base_url=inference.base_url,
        api_key=key)

    def backend(messages, temperature, max_tokens):
        payload = {"model": args.model, "temperature": temperature,
                   "max_tokens": max_tokens, "messages": list(messages)}
        payload.update(request_options)
        resp = base._post(
            payload,
            before_request=launch_limiter.wait)
        metadata = response_metadata(resp, inference)
        metadata["key_source"] = key_source
        return BackendResponse(
            resp["choices"][0]["message"]["content"].strip(), metadata)
    return backend

backend = (lambda *a, **k: "") if args.dry_run else make_backend()
llm = HierLLM(backend, HierCache(CACHE_DIR), args.model,
              prompt_version=PROMPT_VERSION, dry_run=args.dry_run,
              request_options=request_options)

planned_s1_hashes, planned_stage2, reused = set(), 0, 0
t0 = time.time()
jobs = []
for cx in acts:
    ctx = contexts[cx]
    for cond in CONDS:
        cc = ctx["conditions"][cond]
        groups = [cc["groups"][str(g)]["blocks"]
                  for g in range(len(cc["groups"]))]
        s1_h = [payload_hash(args.model, PROMPT_VERSION, "stage1",
                             args.temperature, args.stage1_max_tokens,
                             build_stage1_messages(g, f"group {k+1}"),
                             request_options)
                for k, g in enumerate(groups) if g]
        prev = done.get((cx, cond))
        if prev is not None:
            if (prev.get("context_hash") != cc["context_hash"]
                    or prev.get("stage1_hashes") != s1_h
                    or prev.get("generation_settings_hash") != settings_hash
                    or prev.get("inference") != inference.public_record()):
                sys.exit(
                    f"ABORT: existing row {cx}/{cond} has different context "
                    "or generation hashes; use a new artifact tag.")
            expected_s2 = payload_hash(
                args.model, PROMPT_VERSION, "stage2", args.temperature,
                args.final_max_tokens,
                build_stage2_messages(prev.get("briefs", [])), request_options)
            if prev.get("stage2_hash") != expected_s2:
                sys.exit(f"ABORT: existing Stage-2 hash mismatch for {cx}/{cond}")
            reused += 1
            continue
        planned_s1_hashes.update(
            h for h in s1_h if not (CACHE_DIR / f"{h}.json").exists())
        planned_stage2 += 1
        jobs.append((cx, cond, cc, groups))


def run_job(job):
    cx, cond, cc, groups = job
    res = generate_hierarchical(
        groups, llm, stage1_max_tokens=args.stage1_max_tokens,
        final_max_tokens=args.final_max_tokens, temperature=args.temperature)
    return {
        "celex": cx, "cond": cond, "summary": res["summary"],
        "briefs": res["briefs"], "context_hash": cc["context_hash"],
        "stage1_hashes": res["stage1_hashes"],
        "stage2_hash": res["stage2_hash"],
        "generation_settings_hash": settings_hash,
        "inference": inference.public_record(),
        "stage1_transport": res["stage1_transport"],
        "stage2_transport": res["stage2_transport"],
        "n_groups_used": res["n_groups_used"],
        "evidence_tokens": cc["total_evidence_tokens"],
    }


if not args.dry_run:
    out_f = open(OUT_FP, "a")
    try:
        completed = 0

        def write_row(row):
            out_f.write(json.dumps(row) + "\n")
            out_f.flush()

        if args.workers == 1:
            # Strictly sequential and durable: finish and append one act/arm
            # before launching the next API request chain. This prevents an
            # output/writer failure from leaving pre-submitted jobs draining.
            for job in jobs:
                write_row(run_job(job))
                completed += 1
                if completed % 10 == 0 or completed == len(jobs):
                    print(f"  {completed}/{len(jobs)} new rows | "
                          f"{llm.n_calls} calls | {llm.cache.n_hits} cache hits",
                          flush=True)
        else:
            pool = ThreadPoolExecutor(max_workers=args.workers)
            futures = [pool.submit(run_job, job) for job in jobs]
            try:
                for future in as_completed(futures):
                    write_row(future.result())
                    completed += 1
                    if completed % 10 == 0 or completed == len(jobs):
                        print(f"  {completed}/{len(jobs)} new rows | "
                              f"{llm.n_calls} calls | {llm.cache.n_hits} cache hits",
                              flush=True)
            except BaseException:
                for future in futures:
                    future.cancel()
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            else:
                pool.shutdown(wait=True)
    finally:
        out_f.close()

# ---- manifest ----
try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                     cwd=str(ROOT.parent),
                                     stderr=subprocess.DEVNULL).decode().strip()
except Exception:                                            # noqa: BLE001
    commit = "unavailable (phase3 may be untracked)"
try:
    import transformers, sentence_transformers, numpy
    pkgs = {"transformers": transformers.__version__,
            "sentence_transformers": sentence_transformers.__version__,
            "numpy": numpy.__version__, "python": sys.version.split()[0]}
except Exception:                                            # noqa: BLE001
    pkgs = {"python": sys.version.split()[0]}

manifest = {
    "git_commit": commit,
    "utc": datetime.now(timezone.utc).isoformat(),
    "dataset": "dennlinger/eur-lex-sum", "split": SPLIT,
    "n_acts": len(acts), "celex_ids": acts,
    "model": args.model, "prompt_version": PROMPT_VERSION,
    "inference": inference.public_record(),
    "generation_settings_hash": settings_hash,
    "prompt_sha256": {
        "stage1_system": __import__("hashlib").sha256(
            STAGE1_SYS.encode()).hexdigest(),
        "stage2_system": __import__("hashlib").sha256(
            STAGE2_SYS.encode()).hexdigest()},
    "cli": {k: (str(v) if isinstance(v, Path) else v)
            for k, v in vars(args).items()},
    "hashes": {"contexts": sha256_file(CTX_FP),
               "graph": metadata["graph_sha256"],
               "citation_cards": card_meta["cards_sha256"]},
    "graph_artifact": graph_rel,
    "context_tokenizer": metadata["tokenizer"],
    "context_manifest": CTX_MAN_FP.name,
    "citation_evidence": card_meta,
    "packages": pkgs,
    "dry_run": args.dry_run,
    "llm_calls_made": llm.n_calls,
    "cache_hits": llm.cache.n_hits,
    "rows_reused": reused,
    "elapsed_s": round(time.time() - t0, 1),
    "workers": args.workers,
    "launch_rpm": args.rpm,
}
MAN_FP.write_text(json.dumps(manifest, indent=2))

print(f"\nstage-1 calls that would be NEW: {len(planned_s1_hashes)}")
print(f"stage-2 calls that would be NEW: {planned_stage2}")
print(f"total planned NEW calls: {len(planned_s1_hashes) + planned_stage2}")
print(f"rows reused from a matching previous run: {reused}")
if args.dry_run:
    print(f"\nDRY RUN — {llm.n_calls} API calls made (must be 0)")
else:
    print(f"\nmade {llm.n_calls} calls, {llm.cache.n_hits} cache hits "
          f"-> {OUT_FP.name}")
print(f"manifest -> data/{MAN_FP.name}")
