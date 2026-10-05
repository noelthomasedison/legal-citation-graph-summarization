"""Score the manually labelled Phase 3 v2 graph precision sample.

TRUE/FALSE labels estimate precision; UNSURE is reported and excluded from the
point estimate. Within- and cross-document estimates are shown separately, and
the overall estimate is weighted by their frozen graph population shares.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from context_v2 import sha256_file                         # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--boot", type=int, default=10000)
ap.add_argument("--seed", type=int, default=41)
ap.add_argument("--artifact-tag", default="v2_2")
args = ap.parse_args()

if not all(c.isalnum() or c == "_" for c in args.artifact_tag):
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
SAMPLE = ROOT / "data" / f"eurlex_audit_{args.artifact_tag}_sample.jsonl"
MANIFEST = ROOT / "data" / f"eurlex_audit_{args.artifact_tag}_manifest.json"
OUT = ROOT / "reports" / f"eurlex_audit_{args.artifact_tag}_results.md"

if not SAMPLE.exists() or not MANIFEST.exists():
    sys.exit("run 16_eurlex_audit_v2_sample.py first")
meta = json.loads(MANIFEST.read_text())
graph = ROOT / meta["graph"]
if not graph.exists() or sha256_file(graph) != meta.get("graph_sha256"):
    sys.exit("v2 graph hash differs from the audit manifest; refusing to score")

rows = [json.loads(x) for x in SAMPLE.read_text().splitlines() if x.strip()]
allowed = {"TRUE", "FALSE", "UNSURE"}
bad, missing = [], []
for r in rows:
    label = r.get("label")
    if label is None or str(label).strip() == "":
        missing.append(r["i"])
        continue
    label = str(label).strip().upper()
    if label not in allowed:
        bad.append((r["i"], r.get("label")))
    r["label"] = label
if bad:
    sys.exit("invalid labels: " + ", ".join(f"{i}={v!r}" for i, v in bad))
if missing:
    sys.exit(f"{len(missing)} rows are still unlabelled (first: {missing[:10]})")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


stats = {}
for scope in ("within", "cross"):
    sub = [r for r in rows if r["scope"] == scope]
    true = sum(r["label"] == "TRUE" for r in sub)
    false = sum(r["label"] == "FALSE" for r in sub)
    unsure = sum(r["label"] == "UNSURE" for r in sub)
    decided = true + false
    if decided == 0:
        sys.exit(f"no decided labels in {scope} stratum")
    lo, hi = wilson(true, decided)
    stats[scope] = {"true": true, "false": false, "unsure": unsure,
                    "decided": decided, "precision": true / decided,
                    "lo": lo, "hi": hi}

population = meta["population"]
total_population = sum(population.values())
weights = {k: population[k] / total_population for k in ("within", "cross")}
weighted = sum(weights[k] * stats[k]["precision"] for k in weights)

rng = np.random.default_rng(args.seed)
boots = np.empty(args.boot)
for b in range(args.boot):
    estimate = 0.0
    for scope in ("within", "cross"):
        vals = np.array([1.0 if r["label"] == "TRUE" else 0.0
                         for r in rows
                         if r["scope"] == scope and r["label"] != "UNSURE"])
        estimate += weights[scope] * rng.choice(
            vals, size=len(vals), replace=True).mean()
    boots[b] = estimate
weighted_lo, weighted_hi = np.percentile(boots, [2.5, 97.5])

L = [f"# EUR-Lex {args.artifact_tag} graph precision audit results", "",
     f"Frozen graph sha256: `{meta['graph_sha256'][:16]}…`; UID version `v2`; "
     f"sample seed {meta['seed']}.", "",
     "`UNSURE` rows are reported but excluded from precision denominators.", "",
     "| scope | population | weight | TRUE | FALSE | UNSURE | precision | 95% Wilson CI |",
     "|---|---:|---:|---:|---:|---:|---:|---:|"]
for scope in ("within", "cross"):
    s = stats[scope]
    L.append(f"| {scope} | {population[scope]:,} | {weights[scope]:.3f} | "
             f"{s['true']} | {s['false']} | {s['unsure']} | "
             f"{s['precision']:.3f} | [{s['lo']:.3f}, {s['hi']:.3f}] |")
L += ["", "## Population-weighted overall precision", "",
      f"**{weighted:.3f}**, stratified-bootstrap 95% CI "
      f"[{weighted_lo:.3f}, {weighted_hi:.3f}] ({args.boot:,} resamples, "
      f"seed {args.seed}).", "",
      "The cross-document row is the most relevant precision estimate for",
      "variant B. Overall precision is dominated by within-document edges and",
      "must not be used to hide a weak cross-document result."]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L) + "\n")
print("\n".join(L))
print(f"\nwrote {OUT.relative_to(ROOT)}")
