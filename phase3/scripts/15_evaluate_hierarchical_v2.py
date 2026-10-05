"""Phase 3 v2 — evaluation with pre-registered hypotheses and loss tracing.

PRIMARY   H1  B vs A on b_incremental_actual_rescue_idx only
SECONDARY H2  A vs base on a_actual_rescue_idx
Aggregate     ROUGE-1/2/L, ROUGE-1 precision, BERTScore (descriptive)
Oracle        diagnostic sensitivity analysis ONLY — its selection uses the
              reference, so it cannot demonstrate that a deployable method works

LANGUAGE RULE (enforced in the report text): a result with p >= 0.05 is
reported as "no statistically detectable difference was observed", never as a
confirmed null and never as proof of anything.

Also traces WHERE targeted content is lost across the hierarchy:
    selected evidence  ->  Stage-1 briefs  ->  final summary
distinguishing retrieval failure, compression failure and composition failure.

RePASs is deliberately excluded: the v1 run was stopped and the metric has not
been validated for abstractive EUR-Lex summarisation.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--threshold", type=float, default=0.60)
ap.add_argument("--boot", type=int, default=5000)
ap.add_argument("--seed", type=int, default=41)
ap.add_argument("--artifact-tag", default="",
                help="context/summary suffix created by scripts 13 and 14")
args = ap.parse_args()

SPLIT = args.split
if args.artifact_tag and not args.artifact_tag.replace("_", "").isalnum():
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
tag_suffix = f"_{args.artifact_tag}" if args.artifact_tag else ""
CTX_FP = ROOT / "data" / f"contexts_hier_v2_{SPLIT}{tag_suffix}.json"
CTX_MAN_FP = ROOT / "data" / f"context_manifest_hier_v2_{SPLIT}{tag_suffix}.json"
if not CTX_FP.exists():
    sys.exit("exact-token context artefact missing")
from context_v2 import sha256_file, validate_generation_metadata  # noqa: E402
artifact = json.load(open(CTX_FP))
if artifact.get("schema_version") != "hier-v2.1":
    sys.exit("unsupported or unsafe context schema")
if artifact.get("metadata", {}).get("evidence_representation") != "citation_card":
    sys.exit("evaluation blocked: amended v2 requires citation-card contexts")
try:
    validate_generation_metadata(artifact.get("metadata", {}))
except ValueError as e:
    sys.exit(f"evaluation blocked: {e}")
if not artifact["metadata"].get("valid_for_generation", False):
    sys.exit("evaluation blocked: context audit did not pass all gates")
if not CTX_MAN_FP.exists():
    sys.exit("context manifest missing")
ctx_manifest = json.load(open(CTX_MAN_FP))
if ctx_manifest.get("context_sha256") != sha256_file(CTX_FP):
    sys.exit("context hash does not match its manifest")
CTX = artifact["contexts"]
SUM_FP = ROOT / "data" / f"summaries_hier_v2_{SPLIT}{tag_suffix}.jsonl"
if not SUM_FP.exists():
    sys.exit("no summaries yet — run 14_generate_hierarchical_v2.py")

gen, briefs = {}, {}
for line in open(SUM_FP):
    r = json.loads(line)
    if r["celex"] not in CTX or r["cond"] not in CTX[r["celex"]]["conditions"]:
        sys.exit(f"unknown summary row {r['celex']}/{r['cond']}")
    expected = CTX[r["celex"]]["conditions"][r["cond"]]["context_hash"]
    if r.get("context_hash") != expected:
        sys.exit(f"summary/context hash mismatch for {r['celex']}/{r['cond']}")
    gen.setdefault(r["celex"], {})[r["cond"]] = r["summary"]
    briefs.setdefault(r["celex"], {})[r["cond"]] = r.get("briefs", [])
CONDS = ("base", "A", "B", "oracle")
acts = sorted(c for c in gen if c in CTX and all(x in gen[c] for x in CONDS))
print(f"acts with summaries: {len(acts)}")

import torch                                                   # noqa: E402
from sentence_transformers import SentenceTransformer        # noqa: E402
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"evaluation device: {device}")
sbert = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
QP = "Represent this sentence for searching relevant passages: "

import re                                                    # noqa: E402
_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= 8]


def cover(sent_emb, texts):
    if not texts:
        return np.zeros(sent_emb.shape[0])
    E = sbert.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return (sent_emb @ E.T).max(axis=1)


# ------------------------------------------------ targeted + loss tracing
rows = []
for cx in acts:
    c = CTX[cx]
    gs = c["summary_sentences"]
    if not gs:
        continue
    S = sbert.encode([QP + s for s in gs], normalize_embeddings=True,
                     show_progress_bar=False)
    lab = c["labels"]
    for cond in CONDS:
        if cond not in gen[cx]:
            continue
        cc = c["conditions"][cond]
        ev_texts = [b for g in cc["groups"].values() for b in g["blocks"]]
        cov_ev = cover(S, ev_texts)
        cov_br = cover(S, briefs[cx].get(cond) or [])
        cov_fi = cover(S, sentences(gen[cx][cond]))
        for name, idx in (
                ("h1", lab["b_incremental_actual_rescue_idx"]),
                ("h2", lab["a_actual_rescue_idx"]),
                ("base_missed", lab["base_missed_idx"])):
            if not idx:
                continue
            rows.append({
                "celex": cx, "cond": cond, "target": name, "n": len(idx),
                "evidence": float((cov_ev[idx] >= args.threshold).mean()),
                "brief": float((cov_br[idx] >= args.threshold).mean()),
                "final": float((cov_fi[idx] >= args.threshold).mean()),
                "a_primary_eligible": c["flags"]["a_primary_eligible"],
                "b_primary_eligible": c["flags"]["b_primary_eligible"],
            })

# ------------------------------------------------ paired statistics
try:
    from scipy.stats import wilcoxon
except ImportError:
    wilcoxon = None
rng = np.random.default_rng(args.seed)


def paired(hi, lo, target, stage="final", eligibility=None):
    a = {r["celex"]: r[stage] for r in rows
         if r["cond"] == hi and r["target"] == target
         and (eligibility is None or r[eligibility])}
    b = {r["celex"]: r[stage] for r in rows
         if r["cond"] == lo and r["target"] == target
         and (eligibility is None or r[eligibility])}
    keys = sorted(set(a) & set(b))
    if len(keys) < 3:
        return None
    d = np.array([a[k] - b[k] for k in keys])
    boot = [rng.choice(d, len(d), replace=True).mean() for _ in range(args.boot)]
    lo_ci, hi_ci = np.percentile(boot, [2.5, 97.5])
    p = (wilcoxon(d).pvalue if wilcoxon is not None and np.any(d != 0)
         else float("nan"))
    return {"n": len(keys), "mean": float(d.mean()),
            "lo": float(lo_ci), "hi": float(hi_ci), "p": float(p),
            "wins": int((d > 0).sum()), "ties": int((d == 0).sum()),
            "losses": int((d < 0).sum())}


def verdict(r):
    if r is None:
        return "insufficient data"
    if not np.isnan(r["p"]) and r["p"] < 0.05:
        return "statistically detectable difference"
    return "no statistically detectable difference was observed"


L = ["# Phase 3 v2 — hierarchical summarisation results", "",
     f"Split `{SPLIT}`, {len(acts)} acts with summaries. One-level hierarchy",
     "(evidence -> group briefs -> summary), identical per-group token budget",
     "for every condition. Pre-registered in PHASE3_V2_HIERARCHICAL_PLAN.md.", "",
     "## PRIMARY H1 — variant B vs variant A", "",
     "Measured only on `b_incremental_actual_rescue_idx`: gold sentences that",
     "A's actual evidence did NOT cover and B's actual evidence did. This",
     "isolates what cross-document evidence adds over within-document evidence.",
     "", "| contrast | n | mean d | 95% CI | Wilcoxon p | w/t/l | verdict |",
     "|---|---|---|---|---|---|---|"]
r = paired("B", "A", "h1", eligibility="b_primary_eligible")
if r:
    L.append(f"| B-A (H1) | {r['n']} | {r['mean']:+.4f} | "
             f"[{r['lo']:+.4f}, {r['hi']:+.4f}] | {r['p']:.3g} | "
             f"{r['wins']}/{r['ties']}/{r['losses']} | {verdict(r)} |")
else:
    L.append("| B-A (H1) | — | — | — | — | — | insufficient data |")

L += ["", "### H1 across three populations (reported together)", "",
      "| population | n | mean d | p | verdict |", "|---|---|---|---|---|"]
populations = [
    ("all acts with Base-missed sentences", "base_missed", None),
    ("balanced genuine-B treatment", "base_missed", "b_primary_eligible"),
    ("incremental actual-rescue subset", "h1", "b_primary_eligible"),
]
for label, tgt, eligible in populations:
    rr = paired("B", "A", tgt, eligibility=eligible)
    if rr:
        L.append(f"| {label} | {rr['n']} | {rr['mean']:+.4f} | "
                 f"{rr['p']:.3g} | {verdict(rr)} |")
    else:
        L.append(f"| {label} | — | — | — | insufficient data |")
L += ["", "## SECONDARY H2 — variant A vs base", "",
      "| contrast | n | mean d | 95% CI | Wilcoxon p | w/t/l | verdict |",
      "|---|---|---|---|---|---|---|"]
r2 = paired("A", "base", "h2", eligibility="a_primary_eligible")
if r2:
    L.append(f"| A-base (H2) | {r2['n']} | {r2['mean']:+.4f} | "
             f"[{r2['lo']:+.4f}, {r2['hi']:+.4f}] | {r2['p']:.3g} | "
             f"{r2['wins']}/{r2['ties']}/{r2['losses']} | {verdict(r2)} |")

# ------------------------------------------------ hierarchical loss
L += ["", "## Where targeted content is lost in the hierarchy", "",
      "Coverage of the targeted gold sentences at each stage. A drop between",
      "columns localises the failure:", "",
      "- evidence -> brief: **compression failure** (Stage 1 discarded it)",
      "- brief -> final: **composition failure** (Stage 2 discarded it)",
      "- low at evidence: **retrieval failure** (it never entered the context)",
      "", "| condition | target | n | evidence | brief | final |",
      "|---|---|---|---|---|---|"]
for cond in CONDS:
    for tgt in ("h1", "h2"):
        sub = [r for r in rows if r["cond"] == cond and r["target"] == tgt]
        if not sub:
            continue
        L.append(f"| {cond} | {tgt} | {len(sub)} | "
                 f"{np.mean([s['evidence'] for s in sub]):.3f} | "
                 f"{np.mean([s['brief'] for s in sub]):.3f} | "
                 f"{np.mean([s['final'] for s in sub]):.3f} |")

# ------------------------------------------------ aggregate descriptives
L += ["", "## Aggregate metrics (descriptive only)", ""]
try:
    from rouge_score import rouge_scorer
    from huggingface_hub import hf_hub_download
    gold = {}
    p = hf_hub_download("dennlinger/eur-lex-sum", f"data/english/{SPLIT}.json",
                        repo_type="dataset")
    for line in open(p):
        if line.strip():
            rr = json.loads(line)
            gold[rr["celex_id"]] = rr["summary"]
    rs = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    agg = {c: {"r1": [], "r2": [], "rL": [], "r1p": []} for c in CONDS}
    for cx in acts:
        for c in CONDS:
            if c not in gen[cx] or cx not in gold:
                continue
            sc = rs.score(gold[cx], gen[cx][c])
            agg[c]["r1"].append(sc["rouge1"].fmeasure)
            agg[c]["r2"].append(sc["rouge2"].fmeasure)
            agg[c]["rL"].append(sc["rougeL"].fmeasure)
            agg[c]["r1p"].append(sc["rouge1"].precision)
    L += ["| metric | " + " | ".join(CONDS) + " |",
          "|---|" + "---|" * len(CONDS)]
    for k, lab in (("r1", "ROUGE-1"), ("r2", "ROUGE-2"), ("rL", "ROUGE-L"),
                   ("r1p", "ROUGE-1 precision")):
        L.append(f"| {lab} | " + " | ".join(
            f"{np.mean(agg[c][k]):.4f}" if agg[c][k] else "—" for c in CONDS) + " |")
except Exception as e:                                       # noqa: BLE001
    L.append(f"(ROUGE unavailable: {type(e).__name__}: {e})")

try:
    from bert_score import score as bert_score
    bmeans = {}
    for cond in CONDS:
        pred = [gen[cx][cond] for cx in acts if cx in gold]
        refs = [gold[cx] for cx in acts if cx in gold]
        if not pred:
            bmeans[cond] = float("nan")
            continue
        _, _, f1 = bert_score(pred, refs, lang="en", verbose=False,
                              device=device, batch_size=8)
        bmeans[cond] = float(f1.mean())
    L += ["", "| metric | " + " | ".join(CONDS) + " |",
          "|---|" + "---|" * len(CONDS),
          "| BERTScore-F1 | " + " | ".join(
              f"{bmeans[c]:.4f}" for c in CONDS) + " |"]
except Exception as e:                                       # noqa: BLE001
    L += ["", f"(BERTScore unavailable: {type(e).__name__}: {e})"]

L += ["", "## Oracle arm — diagnostic only", "",
      "Oracle evidence is selected **using the reference summary**. It is",
      "target-leaking and not deployable. It bounds what better evidence",
      "selection could achieve; it does **not** demonstrate that the citation",
      "graph works, and it is not used to support any claim about A or B.", "",
      "## Reporting language", "",
      "Contrasts with p >= 0.05 are reported as *no statistically detectable",
      "difference was observed*. No hypothesis in this report is described as",
      "proved, and no non-significant result is described as a confirmed null.",
      "", "RePASs is not run in v2: the v1 scoring run was stopped, and the",
      "metric has not been validated for abstractive EUR-Lex summarisation."]

OUT = ROOT / "reports" / f"summarisation_hier_v2{tag_suffix}.md"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L) + "\n")
json.dump({"rows": rows}, open(
    ROOT / "data" / f"eval_hier_v2_{SPLIT}{tag_suffix}.json", "w"))
print("\n".join(L[4:]))
print(f"\nwrote reports/{OUT.name}")
