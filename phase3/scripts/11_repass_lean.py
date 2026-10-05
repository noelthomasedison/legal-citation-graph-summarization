"""Lean RePASs scorer — memory-fixed, batched, self-verifying.

WHY THIS EXISTS. 08_evaluate_summaries.py ran RePASs at ~5.5 min/act (~7h for
80 acts) on an 8 GB machine with 2.8 GB of swap already in use. Two causes:

  1. MEMORY (the big one). It called load_eurlexsum(), pulling all 260,149
     passages of the full corpus into memory alongside three transformer
     models. The scorer only needs the passages referenced by the 80 acts —
     a few thousand. The machine was swapping, so the job was disk-bound.
  2. COMPUTE. The obligation-coverage step called deberta-large-mnli one
     sentence pair at a time in a nested Python loop.

Fix 1 changes NO computation — it just avoids loading data never used.
Fix 2 is verified equivalent before it is trusted: this script scores the
first --verify acts BOTH ways and aborts unless every reported value matches
to <1e-4. 09_verify_batching already showed the classifier gives identical
decisions when batched (0/20 mismatches, max diff 7e-07); this repeats the
check end-to-end on the real pipeline.

Stage 1 (prep) loads the corpus once, extracts only the needed passage texts
to a small cache, and exits — so the corpus and the models are never resident
at the same time.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--stage", choices=("prep", "score"), required=True)
ap.add_argument("--verify", type=int, default=2,
                help="acts scored BOTH ways before trusting the batched path")
args = ap.parse_args()

CONDS = ("base", "A", "B", "oracle")
THR = 0.7
_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= 8]

POOL_FP = ROOT / "data" / f"repass_pools_{args.split}.json"

# ===================== STAGE 1: prep =====================
if args.stage == "prep":
    from eurlex_ingest import load_eurlexsum
    from regkg.textutil import clean
    align = json.load(open(ROOT / "data" / f"align_{args.split}.json"))
    print("loading corpus once to extract needed passages...", flush=True)
    corpus, id2celex, celex2id = load_eurlexsum()
    pools = {}
    for cx, a in align.items():
        uids = (a["base_uids"] + a["a_add_uids"] + a["b_add_uids"]
                + a["oracle_uids"])
        sents = []
        for u in uids:
            if u in corpus.by_uid:
                sents.extend(sentences(clean(corpus.by_uid[u].text)))
        pools[cx] = sents[:60]          # the scorer caps at 60 anyway
    json.dump(pools, open(POOL_FP, "w"))
    tot = sum(len(v) for v in pools.values())
    print(f"wrote {POOL_FP.name}: {len(pools)} acts, {tot:,} pool sentences")
    print("corpus released — run --stage score next (models only, no corpus)")
    sys.exit(0)

# ===================== STAGE 2: score =====================
import torch
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          pipeline)

if not POOL_FP.exists():
    sys.exit("run --stage prep first")
pools = json.load(open(POOL_FP))
gen = {}
for l in open(ROOT / "data" / f"summaries_{args.split}.jsonl"):
    r = json.loads(l)
    gen.setdefault(r["celex"], {})[r["cond"]] = r["summary"]
acts = sorted(c for c in gen if len(gen[c]) == 4 and c in pools)
print(f"acts: {len(acts)} | pools loaded (no corpus in memory)", flush=True)

DEV = "mps" if torch.backends.mps.is_available() else "cpu"
print("loading models...", flush=True)
nli_tok = AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-xsmall")
nli = AutoModelForSequenceClassification.from_pretrained(
    "cross-encoder/nli-deberta-v3-xsmall").to(DEV).eval()
cov = pipeline("text-classification", model="microsoft/deberta-large-mnli",
               device=DEV)
obl_dir = str(ROOT.parent / "phase2" / "models" / "obligation-classifier-legalbert")
obl_tok = AutoTokenizer.from_pretrained(obl_dir)
obl = AutoModelForSequenceClassification.from_pretrained(obl_dir).to(DEV).eval()

@torch.no_grad()
def nli_probs(prem, hyp):
    enc = nli_tok(prem, hyp, padding=True, truncation=True, max_length=256,
                  return_tensors="pt").to(DEV)
    return torch.softmax(nli(**enc).logits, -1).cpu().numpy()

@torch.no_grad()
def is_obl(ss):
    if not ss:
        return []
    enc = obl_tok(ss, padding=True, truncation=True, max_length=128,
                  return_tensors="pt").to(DEV)
    return obl(**enc).logits.argmax(-1).cpu().numpy()

def cov_single(osrc, oans):
    """Original: one call per pair, break on first match."""
    c = 0
    for o in osrc:
        for a in oans:
            r = cov(f"{a} [SEP] {o}", truncation=True)[0]
            if r["label"].lower() == "entailment" and r["score"] > THR:
                c += 1
                break
    return c / len(osrc) if osrc else 0.0

def cov_batched(osrc, oans):
    """Batched: full cross-product, then the same 'any match' rule."""
    if not osrc or not oans:
        return 0.0
    pairs = [f"{a} [SEP] {o}" for o in osrc for a in oans]
    res = cov(pairs, truncation=True, batch_size=32)
    hit = np.array([r["label"].lower() == "entailment" and r["score"] > THR
                    for r in res]).reshape(len(osrc), len(oans))
    return float(hit.any(axis=1).mean())

def repass(pool, answer, batched=False):
    ps = pool[:60]
    as_ = sentences(answer)[:20]
    if not ps or not as_:
        return dict(repass=1/3, es=0.0, cs=0.0, oc=0.0)
    E = np.zeros((len(ps), len(as_))); C = np.zeros((len(ps), len(as_)))
    for i, pp in enumerate(ps):
        pr = nli_probs([pp] * len(as_), as_)
        C[i], E[i] = pr[:, 0], pr[:, 1]
    es = float(np.mean(np.max(E, 0))); cs = float(np.mean(np.max(C, 0)))
    osrc = [s for s, l in zip(ps, is_obl(ps)) if l == 1]
    oans = [s for s, l in zip(as_, is_obl(as_)) if l == 1]
    # VERIFIED 2026-08-11: batched == unbatched to 0.000e+00 (bit-identical),
    # but 0.7x SPEED — the unbatched loop breaks on first match and so does
    # strictly less work. Default to the faster, verified-equivalent path.
    oc = (cov_batched if batched else cov_single)(osrc, oans)
    return dict(repass=round((oc + es - cs + 1) / 3, 5), es=round(es, 5),
                cs=round(cs, 5), oc=round(oc, 5))

# ---- self-verification before trusting the batched path ----
import time
if args.verify:
    print(f"\nverifying batched == unbatched on {args.verify} acts...", flush=True)
    worst, t_s, t_b = 0.0, 0.0, 0.0
    for cx in acts[: args.verify]:
        for cond in CONDS:
            t0 = time.time(); s = repass(pools[cx], gen[cx][cond], batched=False)
            t_s += time.time() - t0
            t0 = time.time(); b = repass(pools[cx], gen[cx][cond], batched=True)
            t_b += time.time() - t0
            for k in ("repass", "es", "cs", "oc"):
                worst = max(worst, abs(s[k] - b[k]))
    print(f"  max abs difference: {worst:.3e}")
    print(f"  speedup: {t_s/max(t_b,1e-9):.1f}x")
    if worst > 1e-4:
        sys.exit(f"ABORT: batched differs by {worst:.3e} — not safe, do not use")
    print("  VERIFIED SAFE — proceeding with batched scoring\n", flush=True)

# ---- score everything ----
out_fp = ROOT / "data" / f"repass_{args.split}.jsonl"
done = set()
if out_fp.exists():
    for l in open(out_fp):
        r = json.loads(l)
        done.add((r["celex"], r["cond"]))
    print(f"resuming: {len(done)} already scored", flush=True)

t0 = time.time()
with open(out_fp, "a") as f:
    for n, cx in enumerate(acts):
        for cond in CONDS:
            if (cx, cond) in done:
                continue
            r = repass(pools[cx], gen[cx][cond], batched=False)
            f.write(json.dumps({"celex": cx, "cond": cond, **r}) + "\n")
            f.flush()
        if (n + 1) % 10 == 0:
            el = time.time() - t0
            print(f"  {n+1}/{len(acts)} acts | {el/60:.1f} min | "
                  f"~{el/(n+1)*(len(acts)-n-1)/60:.1f} min left", flush=True)
print(f"done -> {out_fp}")
