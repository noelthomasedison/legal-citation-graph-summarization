"""Run a blinded CoreWeave LLM-as-judge evaluation of frozen summaries.

One request contains the gold summary and four anonymously shuffled candidates
for one act. Requests are sequential, validated against a strict JSON schema,
content-addressed, and checkpointed to JSONL immediately. This is a post-hoc
diagnostic evaluation; it does not change summaries or the pre-registered tests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from citation_evidence_v2 import (  # noqa: E402
    StructuredCache, StructuredLLM, StructuredResponseError, sha256_json,
)
from context_v2 import sha256_file  # noqa: E402
from llm_provider_v2 import (  # noqa: E402
    BackendResponse, RetryableProviderResponseError, chat_completion_text,
    load_api_key, resolve_inference_config, response_metadata,
)
from llm_summary_judge_v2 import (  # noqa: E402
    CONDITIONS, DIMENSIONS, HEADLINE_SCORES, PROMPT_VERSION, SCHEMA_VERSION, blinded_candidates,
    build_messages, macro_score, response_schema, validate_judgement,
)
from regkg.llm_extract import LLMClient  # noqa: E402


ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--artifact-tag", default="citation_card_full_v4")
ap.add_argument("--model", default="openai/gpt-oss-120b")
ap.add_argument("--endpoint-provider", default="coreweave")
ap.add_argument("--quantization", default="fp4")
ap.add_argument("--seed", type=int, default=41)
ap.add_argument("--rpm", type=float, default=12.0)
ap.add_argument("--max-tokens", type=int, default=8192)
ap.add_argument("--reasoning-effort", choices=("low", "medium", "high"),
                default="medium")
ap.add_argument("--limit-acts", type=int, default=0,
                help="deterministic calibration subset; zero means all acts")
ap.add_argument("--boot", type=int, default=5000)
ap.add_argument("--schema-retries", type=int, default=3,
                help="retry provider outputs that fail the frozen JSON validator")
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

if not args.artifact_tag.replace("_", "").isalnum():
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
if not 1 <= args.rpm <= 60:
    sys.exit("--rpm must be between 1 and 60")
if args.limit_acts < 0:
    sys.exit("--limit-acts cannot be negative")
if not 1 <= args.schema_retries <= 5:
    sys.exit("--schema-retries must be between 1 and 5")

try:
    inference = resolve_inference_config(
        "openrouter", args.model, args.endpoint_provider, args.quantization, False)
except ValueError as exc:
    sys.exit(str(exc))

safe_model = args.model.replace("/", "_").replace("-", "_")
judge_run_tag = f"{safe_model}_m{args.max_tokens}"
SUM_FP = ROOT / "data" / f"summaries_hier_v2_{args.split}_{args.artifact_tag}.jsonl"
OUT = ROOT / "data" / (
    f"llm_judgements_hier_v2_{args.split}_{args.artifact_tag}_{judge_run_tag}.jsonl")
MANIFEST = OUT.with_name(OUT.stem + "_manifest.json")
EVAL_JSON = ROOT / "data" / (
    f"eval_llm_judge_hier_v2_{args.split}_{args.artifact_tag}_{judge_run_tag}.json")
REPORT = ROOT / "reports" / (
    f"llm_judge_hier_v2_{args.split}_{args.artifact_tag}_{judge_run_tag}.md")
CACHE = ROOT / "data" / "llm_summary_judge_v2_cache"

if not SUM_FP.exists():
    sys.exit(f"frozen summary artefact missing: {SUM_FP}")


def load_summaries(path: Path) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    seen = set()
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row.get("celex"), row.get("cond"))
        if key in seen:
            raise ValueError(f"duplicate summary at line {lineno}: {key}")
        seen.add(key)
        if row.get("cond") not in CONDITIONS or not str(row.get("summary", "")).strip():
            raise ValueError(f"invalid summary at line {lineno}")
        grouped[row["celex"]][row["cond"]] = row["summary"]
    incomplete = [celex for celex, values in grouped.items()
                  if set(values) != set(CONDITIONS)]
    if incomplete:
        raise ValueError(f"incomplete four-condition acts: {incomplete[:5]}")
    return dict(grouped)


try:
    summaries = load_summaries(SUM_FP)
except (ValueError, json.JSONDecodeError) as exc:
    sys.exit(f"invalid summary artefact: {exc}")

try:
    from huggingface_hub import hf_hub_download
    gold_path = Path(hf_hub_download(
        "dennlinger/eur-lex-sum", f"data/english/{args.split}.json",
        repo_type="dataset", local_files_only=True))
except Exception as exc:
    sys.exit(f"cached EUR-Lex-Sum gold file unavailable: {exc}")

gold = {}
for line in gold_path.read_text().splitlines():
    if line.strip():
        row = json.loads(line)
        gold[row["celex_id"]] = row["summary"]
acts = sorted(set(summaries) & set(gold))
if len(acts) != len(summaries):
    sys.exit("some generated acts have no gold summary")

# The pilot is selected without looking at any summary or score.
pilot_order = sorted(
    acts, key=lambda x: hashlib.sha256(f"pilot|{args.seed}|{x}".encode()).hexdigest())
selected_acts = pilot_order[:args.limit_acts] if args.limit_acts else acts

schema = response_schema(["S1", "S2", "S3", "S4"])
response_format = {
    "type": "json_schema",
    "json_schema": {"name": "legal_summary_evaluation", "strict": True,
                    "schema": schema},
}
request_options = {
    **inference.request_options(),
    "response_format": response_format,
    "reasoning": {"effort": args.reasoning_effort, "exclude": True},
    "seed": args.seed,
}
run_config = {
    "schema_version": SCHEMA_VERSION,
    "prompt_version": PROMPT_VERSION,
    "inference": inference.public_record(),
    "request_options": request_options,
    "temperature": 0.0,
    "max_tokens": args.max_tokens,
    "seed": args.seed,
    "summary_sha256": sha256_file(SUM_FP),
    "gold_sha256": sha256_file(gold_path),
}
run_config_hash = sha256_json(run_config)

done = {}
if OUT.exists():
    for lineno, line in enumerate(OUT.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        celex = row.get("celex")
        if celex in done or celex not in acts:
            sys.exit(f"invalid/duplicate resumed judgement at line {lineno}")
        if row.get("run_config_hash") != run_config_hash:
            sys.exit("existing judgements use a different configuration; rename/remove "
                     "that artefact or restore the original settings")
        done[celex] = row


class LaunchRateLimiter:
    def __init__(self, rpm: float):
        self.interval = 60.0 / rpm
        self.next_start = 0.0

    def wait(self):
        delay = max(0.0, self.next_start - time.monotonic())
        if delay:
            time.sleep(delay)
        self.next_start = time.monotonic() + self.interval


limiter = LaunchRateLimiter(args.rpm)
key, key_source = load_api_key(inference, ROOT.parent / "phase1")
if not args.dry_run and not key:
    sys.exit("no OpenRouter key; set OPENROUTER_API_KEY or phase1/.openrouter_api_key")
client = None if args.dry_run else LLMClient(
    cache_dir=CACHE / "transport", model=inference.model,
    base_url=inference.base_url, api_key=key)


def backend(messages, temperature, max_tokens):
    payload = {
        "model": inference.model, "messages": list(messages),
        "temperature": temperature, "max_tokens": max_tokens,
        **request_options,
    }
    response = client._post(payload, before_request=limiter.wait)
    metadata = response_metadata(response, inference)
    metadata["finish_reason"] = response.get("choices", [{}])[0].get("finish_reason")
    metadata["key_source"] = key_source
    actual = str(metadata.get("actual_provider") or "").lower().replace(" ", "")
    expected = str(inference.endpoint_provider).lower().replace(" ", "")
    if actual and expected not in actual:
        raise RuntimeError(
            f"provider isolation failed: expected {inference.endpoint_provider}, "
            f"received {metadata.get('actual_provider')}")
    return BackendResponse(chat_completion_text(response), metadata)


judge = StructuredLLM(
    backend if not args.dry_run else (lambda *a: ""),
    StructuredCache(CACHE / "responses"), inference.model,
    dry_run=args.dry_run, request_options=request_options)


def append_checkpoint(row: dict):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


print(f"judge model: {inference.model}")
print(f"pinned route: {inference.endpoint_provider} / {inference.quantization}; fallbacks off")
print(f"selected acts: {len(selected_acts)}; already completed: "
      f"{sum(a in done for a in selected_acts)}")
t0 = time.time()
for index, celex in enumerate(selected_acts, 1):
    if celex in done:
        print(f"  [{index}/{len(selected_acts)}] {celex}: checkpoint hit")
        continue
    blinded, mapping = blinded_candidates(celex, summaries[celex], args.seed)
    messages = build_messages(celex, gold[celex], blinded)
    validator = lambda value: validate_judgement(value, list(blinded))
    if args.dry_run:
        _, request_hash = judge.complete(
            "summary_judge", PROMPT_VERSION, messages, args.max_tokens,
            validator, temperature=0.0)
        print(f"  [{index}/{len(selected_acts)}] {celex}: planned {request_hash[:12]}")
        continue
    result = request_hash = None
    last_error = None
    structured_attempts = 0
    for structured_attempts in range(1, args.schema_retries + 1):
        try:
            result, request_hash = judge.complete(
                "summary_judge", PROMPT_VERSION, messages, args.max_tokens,
                validator, temperature=0.0)
            break
        except (StructuredResponseError, RetryableProviderResponseError) as exc:
            last_error = exc
            print(f"  [{index}/{len(selected_acts)}] {celex}: schema retry "
                  f"{structured_attempts}/{args.schema_retries} ({exc})")
    if result is None:
        sys.exit(f"structured judge response failed for {celex} after "
                 f"{args.schema_retries} attempts: {last_error}")
    transport = judge.transport_for(request_hash) or {}
    row = {
        "schema_version": SCHEMA_VERSION,
        "celex": celex,
        "blind_map": mapping,
        "evaluations": result["evaluations"],
        "request_hash": request_hash,
        "structured_attempts": structured_attempts,
        "run_config_hash": run_config_hash,
        "transport": transport,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    append_checkpoint(row)
    done[celex] = row
    usage = transport.get("usage", {})
    print(f"  [{index}/{len(selected_acts)}] {celex}: saved "
          f"({usage.get('total_tokens', '?')} tokens)")

if args.dry_run:
    print("dry run complete; no API calls or result files written")
    raise SystemExit(0)


def explode(rows):
    records = []
    for row in rows:
        for evaluation in row["evaluations"]:
            cond = row["blind_map"][evaluation["candidate_id"]]
            records.append({"celex": row["celex"], "cond": cond,
                            "macro_score": macro_score(evaluation), **evaluation})
    return records


completed_rows = [done[a] for a in selected_acts if a in done]
records = explode(completed_rows)
rng = np.random.default_rng(args.seed)
try:
    from scipy.stats import wilcoxon
except ImportError:
    wilcoxon = None


def paired(hi, lo, metric):
    def score(row):
        if metric == "macro_score":
            return row[metric]
        return row["headline_scores"][metric]
    h = {r["celex"]: score(r) for r in records if r["cond"] == hi}
    l = {r["celex"]: score(r) for r in records if r["cond"] == lo}
    keys = sorted(set(h) & set(l))
    diffs = np.array([h[k] - l[k] for k in keys], dtype=float)
    boots = [float(rng.choice(diffs, len(diffs), replace=True).mean())
             for _ in range(args.boot)] if len(diffs) else []
    p = (float(wilcoxon(diffs).pvalue)
         if wilcoxon is not None and len(diffs) >= 3 and np.any(diffs != 0)
         else None)
    return {
        "n": len(keys), "mean_difference": float(diffs.mean()) if len(diffs) else None,
        "ci95": ([float(x) for x in np.percentile(boots, [2.5, 97.5])]
                 if boots else None),
        "wilcoxon_p": p, "wins": int((diffs > 0).sum()),
        "ties": int((diffs == 0).sum()), "losses": int((diffs < 0).sum()),
    }


means = {}
flags = {}
for cond in CONDITIONS:
    subset = [r for r in records if r["cond"] == cond]
    means[cond] = {
        "macro_score": float(np.mean([r["macro_score"] for r in subset])),
        **{name: float(np.mean([r["headline_scores"][name] for r in subset]))
           for name in HEADLINE_SCORES},
        **{name: float(np.mean([r["scores"][name] for r in subset]))
           for name in DIMENSIONS},
    }
    flags[cond] = {
        name: float(np.mean([r[name] for r in subset]))
        for name in ("material_error", "material_omission",
                     "not_confirmed_by_reference")
    }
contrasts = {
    metric: {"A-base": paired("A", "base", metric),
             "B-A": paired("B", "A", metric),
             "oracle-base": paired("oracle", "base", metric)}
    for metric in HEADLINE_SCORES
}
provider_counts = Counter(
    str(row.get("transport", {}).get("actual_provider") or "unreported")
    for row in completed_rows)
usage_totals = Counter()
for row in completed_rows:
    for key_name, value in row.get("transport", {}).get("usage", {}).items():
        if isinstance(value, (int, float)):
            usage_totals[key_name] += value

evaluation = {
    "schema_version": SCHEMA_VERSION,
    "status": "complete" if len(completed_rows) == len(acts) else "calibration_subset",
    "n_acts": len(completed_rows), "n_total_acts": len(acts),
    "conditions": list(CONDITIONS), "headline_scores": list(HEADLINE_SCORES),
    "dimensions": list(DIMENSIONS),
    "means": means, "flag_rates": flags, "paired_contrasts": contrasts,
    "provider_counts": dict(provider_counts), "usage_totals": dict(usage_totals),
    "run_config": run_config, "run_config_hash": run_config_hash,
    "result_jsonl": str(OUT),
}
EVAL_JSON.write_text(json.dumps(evaluation, indent=2, ensure_ascii=False))

lines = [
    "# Phase 3 v2 — blinded LLM summary evaluation", "",
    f"Status: **{evaluation['status']}** ({len(completed_rows)}/{len(acts)} acts).",
    f"Judge: `{args.model}`, pinned to `{args.endpoint_provider}` "
    f"`{args.quantization}` with provider fallbacks disabled.", "",
    "This is a **post-hoc diagnostic**, additional to ROUGE/BERTScore and the "
    "pre-registered hypothesis tests. For every act, Base/A/B/Oracle were "
    "anonymised and deterministically shuffled before the judge saw them. The "
    "gold summary and all four candidates were evaluated in the same request.", "",
    "The gold summary is a public-facing comparison reference, not a guarantee "
    "that every extra candidate claim is false. No source act text was supplied, "
    "so legal detail absent from the gold cannot be independently assessed.", "",
    "## Headline comparison scores", "",
    "All scores use 1 (unusable) to 5 (excellent). `user` assesses a clear, "
    "accurate public-facing explanation; `legal` assesses preservation of the "
    "material legal meaning represented in the gold.", "",
    "| condition | user comparison | legal comparison |",
    "|---|---:|---:|",
]
for cond in CONDITIONS:
    m = means[cond]
    lines.append(f"| {cond} | {m['user_comparison']:.3f} | "
                 f"{m['legal_comparison']:.3f} |")
lines += ["", "## Diagnostic dimension scores", "",
          "`macro` is the unweighted mean of the six diagnostic dimensions.", "",
          "| condition | macro | fidelity | coverage | salience | lay clarity | practical | concision |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
for cond in CONDITIONS:
    m = means[cond]
    lines.append(f"| {cond} | {m['macro_score']:.3f} | {m['legal_fidelity']:.3f} | "
                 f"{m['material_coverage']:.3f} | {m['legal_salience']:.3f} | "
                 f"{m['lay_clarity']:.3f} | {m['practical_understanding']:.3f} | "
                 f"{m['concision']:.3f} |")
lines += ["", "## Paired exploratory contrasts", "",
          "These comparisons are descriptive/post-hoc, not new confirmatory tests.", "",
          "| perspective | contrast | n | mean difference | 95% bootstrap CI | Wilcoxon p | W/T/L |",
          "|---|---|---:|---:|---:|---:|---:|"]
for metric in HEADLINE_SCORES:
    for label, result in contrasts[metric].items():
        ci = (f"[{result['ci95'][0]:+.3f}, {result['ci95'][1]:+.3f}]"
              if result["ci95"] else "—")
        p = f"{result['wilcoxon_p']:.4g}" if result["wilcoxon_p"] is not None else "—"
        lines.append(
            f"| {metric.replace('_comparison', '')} | {label} | {result['n']} | "
            f"{result['mean_difference']:+.3f} | {ci} | {p} | "
            f"{result['wins']}/{result['ties']}/{result['losses']} |")
lines += ["", "## Diagnostic flag rates", "",
          "| condition | material error | material omission | not confirmed by reference |",
          "|---|---:|---:|---:|"]
for cond in CONDITIONS:
    f = flags[cond]
    lines.append(f"| {cond} | {f['material_error']:.1%} | "
                 f"{f['material_omission']:.1%} | "
                 f"{f['not_confirmed_by_reference']:.1%} |")
lines += ["", "## Provenance", "",
          f"- Actual providers: `{dict(provider_counts)}`",
          f"- Usage: `{dict(usage_totals)}`",
          f"- Prompt version: `{PROMPT_VERSION}`",
          f"- Run configuration hash: `{run_config_hash}`",
          f"- Runtime this invocation: `{(time.time() - t0) / 60:.1f} minutes`",
          "- Candidate condition mapping is retained in the machine-readable "
          "JSONL but was never included in judge prompts."]
REPORT.write_text("\n".join(lines) + "\n")

manifest = {
    "schema_version": SCHEMA_VERSION,
    "status": evaluation["status"],
    "n_completed": len(completed_rows), "n_total": len(acts),
    "judgements_sha256": sha256_file(OUT),
    "evaluation_sha256": sha256_file(EVAL_JSON),
    "report_sha256": sha256_file(REPORT),
    "run_config": run_config, "run_config_hash": run_config_hash,
    "updated_at_utc": datetime.now(timezone.utc).isoformat(),
}
MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
print(f"status: {evaluation['status']}; {len(completed_rows)}/{len(acts)} acts")
print(f"report: {REPORT}")
